"""Prepare a private read-only sharing environment; does not start/restart any service."""
import os
import secrets
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'config/team-share.env'
if target.exists():
    print('기존 config/team-share.env 유지. 새 접속 키를 만들지 않았습니다.')
else:
    values={}
    for line in (ROOT/'.env').read_text().splitlines():
        line=line.strip()
        if line and not line.startswith('#') and '=' in line:
            name,value=line.split('=',1);values[name]=value.strip().strip('\"\'')
    if not values.get('DATABASE_URL_READ'):raise SystemExit('DATABASE_URL_READ가 필요합니다. 관리자 연결로 대체하지 않습니다.')
    descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w') as stream:
        stream.write('DATABASE_URL_READ='+values['DATABASE_URL_READ']+'\nTEAM_ACCESS_TOKEN='+secrets.token_urlsafe(32)+'\n')
    print('config/team-share.env 준비 완료(권한600). 접속 키는 해당 파일에서 확인하세요. 파일 전체/DB URL은 공유하지 마세요.')
