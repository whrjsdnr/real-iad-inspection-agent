"""기존 SQLite를 읽기 전용으로 PostgreSQL 빈 DB에 이관한다. 기존 대상 행은 덮어쓰지 않는다."""
from pathlib import Path
import argparse,json,os
from sqlalchemy import create_engine,select,func,text,Table,MetaData,inspect
from app.models import Base

def transfer(source,destination):
    source=Path(source).resolve()
    src=create_engine(f'sqlite:///file:{source}?mode=ro&uri=true')
    dst=create_engine(destination);counts={}
    # 전체 테이블 이관을 하나의 트랜잭션으로 묶어 부분 성공을 방지한다.
    with src.connect() as read, dst.begin() as write:
        for table in Base.metadata.sorted_tables:
            n=write.scalar(select(func.count()).select_from(table))
            if n:raise ValueError(f'{table.name}: 대상에 기존 행이 있어 자동 이관을 중단합니다')
        for table in Base.metadata.sorted_tables:
            if inspect(read).has_table(table.name):
                source_table=Table(table.name,MetaData(),autoload_with=read)
                extra=set(source_table.columns.keys())-set(table.columns.keys())
                if extra:raise ValueError(f'{table.name}: 미지원 원본 컬럼 보존 필요 {sorted(extra)}')
                rows=[dict(r) for r in read.execute(select(source_table)).mappings().all()]
            else:rows=[]
            if rows:write.execute(table.insert(),[dict(r) for r in rows])
            target=write.scalar(select(func.count()).select_from(table))
            if target!=len(rows):raise ValueError(f'{table.name}: 행 수 불일치')
            counts[table.name]={'source':len(rows),'destination':target}
        if dst.dialect.name=='postgresql':
            write.execute(text("SELECT setval(pg_get_serial_sequence('metrics_snapshots','snapshot_id'), COALESCE(MAX(snapshot_id),1), MAX(snapshot_id) IS NOT NULL) FROM metrics_snapshots"))
    return counts

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    url=os.environ.get('DATABASE_URL')
    if not url or not url.startswith('postgresql'):p.error('대상 DATABASE_URL은 PostgreSQL이어야 합니다')
    result=transfer(a.source,url);a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
