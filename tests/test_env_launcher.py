from pathlib import Path
import subprocess,sys,json

def test_env_file_literal_and_no_shell_evaluation(tmp_path):
 p=tmp_path/'sample.env';p.write_text('TEST_ENV_LITERAL="dollar $VALUE; not a command"\n')
 script=Path(__file__).resolve().parents[1]/'scripts/with_env.py'
 r=subprocess.run([sys.executable,str(script),'--env-file',str(p),'--',sys.executable,'-c','import os,json;print(json.dumps(os.getenv("TEST_ENV_LITERAL")))'],capture_output=True,text=True)
 assert r.returncode==0 and json.loads(r.stdout)=='dollar $VALUE; not a command'

def test_no_implicit_database_target(monkeypatch,tmp_path):
 from import_score_batch import ingest
 monkeypatch.delenv('DATABASE_URL',raising=False);monkeypatch.delenv('DATABASE_URL_BATCH',raising=False)
 import pytest
 with pytest.raises(ValueError,match='명시'):ingest(tmp_path/'missing.db',tmp_path)
