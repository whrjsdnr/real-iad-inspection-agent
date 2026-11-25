"""Authenticated, read-only team GUI. Separate service; no production startup hooks."""
import hashlib
import hmac
import os
import secrets
import time
import copy
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse,JSONResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from .readonly_api import app as readonly_app, lifespan as readonly_lifespan

ROOT=Path(__file__).resolve().parents[1]
COOKIE='inspection_team_session'
MAX_AGE=8*60*60


def secret():
    value=os.getenv('TEAM_ACCESS_TOKEN','')
    if len(value)<32:raise RuntimeError('TEAM_ACCESS_TOKEN must contain at least32characters')
    return value


def session(value,now=None):
    now=int(time.time() if now is None else now)
    try:
        expiry,nonce,signature=value.split('.')
        if not now<int(expiry)<=now+MAX_AGE:return False
        message=f'{expiry}.{nonce}'
        expected=hmac.new(secret().encode(),message.encode(),hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature,expected)
    except (ValueError,TypeError,AttributeError):return False


def issue_session(now=None):
    expiry=int(time.time() if now is None else now)+MAX_AGE
    message=f'{expiry}.{secrets.token_hex(16)}'
    return message+'.'+hmac.new(secret().encode(),message.encode(),hashlib.sha256).hexdigest()


@asynccontextmanager
async def lifespan(app):
    secret()
    async with readonly_lifespan(readonly_app):yield


app=FastAPI(title='Inspection team read-only sharing',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)


@app.middleware('http')
async def authenticate(request:Request,call_next):
    bearer=request.headers.get('authorization','')
    bearer_ok=request.url.path.startswith('/api/') and bearer.startswith('Bearer ') and hmac.compare_digest(bearer[7:],secret())
    if request.url.path!='/team/login' and not bearer_ok and not session(request.cookies.get(COOKIE,'')):
        if request.url.path.startswith('/api/'):
            return JSONResponse({'detail':'팀 공유 로그인이 필요합니다.'},status_code=401)
        return RedirectResponse('/team/login',status_code=303)
    response=await call_next(request)
    response.headers['Cache-Control']='private, no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    return response


@app.get('/team/login',response_class=HTMLResponse)
def login_form():
    tokens=(ROOT/'inspection-gui/src/styles/tokens.css').read_text()
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>검사 데이터 팀 공유</title><style>'+tokens+'body{background:var(--bg);color:var(--text);font:16px system-ui;max-width:420px;margin:12vh auto;padding:24px}input,button{box-sizing:border-box;width:100%;padding:12px;margin-top:12px;background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:8px}</style><h1>검사 데이터 팀 공유</h1><p>같은 중앙 데이터의 읽기 전용 조회</p><form method="post"><label>팀 접속 키<input name="token" type="password" required autocomplete="current-password"></label><button>접속</button></form></html>'


@app.post('/team/login')
async def login(request:Request):
    origin=request.headers.get('origin')
    if origin and origin!=str(request.base_url).rstrip('/'):
        return JSONResponse({'detail':'다른 출처의 로그인 요청은 허용하지 않습니다.'},status_code=403)
    data=await request.form()
    if not hmac.compare_digest(str(data.get('token','')),secret()):
        return JSONResponse({'detail':'접속 키가 올바르지 않습니다.'},status_code=401)
    response=RedirectResponse('/#/dashboard',status_code=303)
    response.set_cookie(COOKIE,issue_session(),httponly=True,samesite='strict',secure=os.getenv('TEAM_COOKIE_SECURE')=='1',max_age=MAX_AGE)
    return response


@app.get('/api/health')
async def health():return {'status':'ok','read_only':True,'sharing':True,'llm':{'mode':'unavailable'}}


@app.get('/api/openapi.json')
async def shared_openapi():
    spec=copy.deepcopy(readonly_app.openapi())
    spec.setdefault('components',{}).setdefault('securitySchemes',{})['TeamBearer']={'type':'http','scheme':'bearer'}
    spec['security']=[{'TeamBearer':[]}];spec['servers']=[{'url':'/api'}]
    return spec


# Separate localhost GUIs can use a header token; no credential is put in URLs.
# CORS must be outermost so unauthenticated browser preflight can be answered.
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv('TEAM_ALLOWED_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(',') if origin.strip()],
    allow_credentials=True,allow_methods=['GET','POST','OPTIONS'],allow_headers=['Authorization','Content-Type'])


app.mount('/api',readonly_app)
app.mount('/',StaticFiles(directory=str(ROOT/'inspection-gui/dist'),html=True,check_dir=False),name='gui')
