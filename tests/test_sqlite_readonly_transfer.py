import sqlite3,hashlib
import pytest
from sqlalchemy import create_engine,text
from app.models import Base
from sqlite_to_pg import transfer

def test_legacy_nullable_columns_reflected_without_source_changes(tmp_path):
 source=tmp_path/'source.db';target=tmp_path/'target.db'
 with sqlite3.connect(source) as c:
  c.execute('CREATE TABLE metrics_snapshots (snapshot_id INTEGER PRIMARY KEY, metric TEXT, definition_version TEXT)')
  c.execute("INSERT INTO metrics_snapshots VALUES (1,'legacy','v1')")
 before=hashlib.sha256(source.read_bytes()).hexdigest()
 engine=create_engine('sqlite:///'+str(target));Base.metadata.create_all(engine)
 result=transfer(source,'sqlite:///'+str(target))
 assert result['metrics_snapshots']=={'source':1,'destination':1}
 assert hashlib.sha256(source.read_bytes()).hexdigest()==before
 with engine.connect() as c:assert c.execute(text('SELECT source_scope FROM metrics_snapshots')).scalar() is None
 with pytest.raises(ValueError,match='기존 행'):transfer(source,'sqlite:///'+str(target))

def test_unknown_source_columns_are_not_silently_discarded(tmp_path):
 source=tmp_path/'source.db';target=tmp_path/'target.db'
 with sqlite3.connect(source) as c:c.execute('CREATE TABLE metrics_snapshots (private_legacy_field TEXT)')
 engine=create_engine('sqlite:///'+str(target));Base.metadata.create_all(engine)
 with pytest.raises(ValueError,match='원본 컬럼'):transfer(source,'sqlite:///'+str(target))
