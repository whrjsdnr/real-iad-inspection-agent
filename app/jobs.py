"""Durable jobs in a separate local SQLite file; no inspection schema changes.

Only this worker's QUEUED work can be cancelled. RUNNING inference is never killed.
One job is claimed with compare-and-swap. A lost RUNNING lease is FAILED on an
explicit administrative recovery, never silently rerun after a worker crash.
"""
from __future__ import annotations
import hashlib,json,sqlite3,threading,uuid
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path

STATES=('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED')
TERMINAL=frozenset(STATES[2:])

def now():return datetime.now(timezone.utc).isoformat()

class JobConflict(ValueError):pass
class QueueFull(RuntimeError):pass

class JobStore:
    def __init__(self,path:Path,capacity=12):
        self.path=Path(path).resolve();self.capacity=capacity
        if self.path.name in ('inspection.db','hvq_max16.sqlite') or self.path.suffix!='.sqlite':
            raise ValueError('Jobs require a dedicated .sqlite file')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connection() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS gui_jobs (
            id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL UNIQUE, payload TEXT NOT NULL,
            state TEXT NOT NULL, stage TEXT NOT NULL, result TEXT, error TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS gui_job_keys (key TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL,job_id TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS gui_job_queue ON gui_jobs(state,created_at);''')

    @contextmanager
    def connection(self):
        c=sqlite3.connect(self.path,timeout=5);c.row_factory=sqlite3.Row
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:c.close()

    def submit(self,payload,key,*,identity=None):
        if not key or len(key)>128:raise ValueError('Idempotency-Key is required (1..128 chars)')
        encoded=json.dumps(payload,sort_keys=True,separators=(',',':'))
        digest=hashlib.sha256(json.dumps(identity if identity is not None else payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            previous=c.execute('SELECT fingerprint,job_id FROM gui_job_keys WHERE key=?',(key,)).fetchone()
            if previous:
                if previous['fingerprint']!=digest:raise JobConflict('Idempotency key already belongs to different input')
                return self.get(previous['job_id']),False
            found=c.execute('SELECT id FROM gui_jobs WHERE fingerprint=?',(digest,)).fetchone()
            if found:job_id=found['id'];created=False
            else:
                if c.execute("SELECT count(*) FROM gui_jobs WHERE state IN ('QUEUED','RUNNING')").fetchone()[0]>=self.capacity:raise QueueFull('Development queue is full')
                job_id=uuid.uuid4().hex;timestamp=now()
                c.execute('INSERT INTO gui_jobs VALUES(?,?,?,?,?,?,?,?,?)',(job_id,digest,encoded,'QUEUED','작업 대기',None,None,timestamp,timestamp));created=True
            c.execute('INSERT INTO gui_job_keys VALUES(?,?,?)',(key,digest,job_id))
        return self.get(job_id),created

    def get(self,job_id,*,internal=False):
        with self.connection() as c:row=c.execute('SELECT * FROM gui_jobs WHERE id=?',(job_id,)).fetchone()
        if row is None:raise KeyError(job_id)
        out=dict(row);out['result']=json.loads(out['result']) if out['result'] else None
        if internal:out['payload']=json.loads(out['payload'])
        else:out.pop('payload');out.pop('fingerprint')
        out['progress']=None
        return out

    def claim(self):
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute("SELECT id FROM gui_jobs WHERE state='QUEUED' ORDER BY created_at,id LIMIT 1").fetchone()
            if not row:return None
            changed=c.execute("UPDATE gui_jobs SET state='RUNNING',stage='처리 시작',updated_at=? WHERE id=? AND state='QUEUED'",(now(),row['id'])).rowcount
        return self.get(row['id'],internal=True) if changed else None

    def finish(self,job_id,*,result=None,error=None):
        state='FAILED' if error is not None else 'COMPLETED'
        with self.connection() as c:
            changed=c.execute("UPDATE gui_jobs SET state=?,stage=?,result=?,error=?,updated_at=? WHERE id=? AND state='RUNNING'",(state,'처리 실패' if error else '처리 완료',json.dumps(result,ensure_ascii=False) if error is None else None,error,now(),job_id)).rowcount
        if not changed:raise JobConflict('Only RUNNING jobs can finish')

    def cancel(self,job_id):
        with self.connection() as c:
            changed=c.execute("UPDATE gui_jobs SET state='CANCELLED',stage='대기 취소',updated_at=? WHERE id=? AND state='QUEUED'",(now(),job_id)).rowcount
        if not changed:
            current=self.get(job_id)
            if current['state']!='CANCELLED':raise JobConflict('Only QUEUED jobs can be cancelled; running inference is not interrupted')
        return self.get(job_id)

    def run_once(self,processor):
        job=self.claim()
        if not job:return False
        try:self.finish(job['id'],result=processor(job['payload']))
        except Exception as exc:self.finish(job['id'],error=f'{type(exc).__name__}: {exc}')
        return True

class JobWorker:
    def __init__(self,store,processor):
        self.store=store;self.processor=processor;self.stop_event=threading.Event();self.thread=None
    def start(self):
        if self.thread is not None:raise RuntimeError('Worker already started')
        import fcntl
        self.lease=self.store.path.with_suffix('.worker.lock').open('a')
        try:fcntl.flock(self.lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as e:
            self.lease.close()
            raise RuntimeError('A worker already owns this development queue') from e
        self.thread=threading.Thread(target=self._run,name='isolated-gui-job-worker',daemon=True);self.thread.start()
    def _run(self):
        try:
            while not self.stop_event.is_set():
                if not self.store.run_once(self.processor):self.stop_event.wait(.5)
        finally:
            self.lease.close()
    def close(self):
        # Finish current job naturally; no subprocess signalling or forced join.
        self.stop_event.set()
