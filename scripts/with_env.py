"""신뢰하는 로컬 .env의 단일행 KEY=VALUE를 코드 실행 없이 환경변수로 로드한다."""
import argparse,os,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--env-file',type=Path,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
command=a.command[1:] if a.command[:1]==['--'] else a.command
if not command:p.error('실행할 명령이 필요합니다')
env=os.environ.copy()
for line in a.env_file.read_text().splitlines():
 line=line.strip()
 if not line or line.startswith('#'):continue
 key,sep,value=line.partition('=')
 if not sep or not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',key):raise ValueError('지원하지 않는 env 행')
 if len(value)>1 and value[0]==value[-1] and value[0] in ['\"',"'"]:value=value[1:-1]
 env[key]=value
os.execvpe(command[0],command,env)
