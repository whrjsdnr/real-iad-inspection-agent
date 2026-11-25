"""스냅샷 CSV 익스포트. reference/measured 출처 컬럼을 그대로 유지한다."""
import sys,csv,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.models import MetricsSnapshot
from app.db import get_engine
from sqlalchemy import select
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
with get_engine('read').connect() as c:rows=c.execute(select(MetricsSnapshot.__table__)).mappings().all()
with a.output.open('x',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(MetricsSnapshot.__table__.columns.keys()));w.writeheader();w.writerows([dict(r) for r in rows])
print(len(rows))
