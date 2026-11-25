from app.team_api import issue_session,session


def test_team_session_is_signed_expires_and_contains_no_access_token(monkeypatch):
    token='x'*40;monkeypatch.setenv('TEAM_ACCESS_TOKEN',token)
    cookie=issue_session(now=1000)
    assert token not in cookie and session(cookie,now=1001)
    assert not session(cookie+'bad',now=1001)
    assert not session(cookie,now=1000+8*60*60)
    monkeypatch.setenv('TEAM_ACCESS_TOKEN','y'*40)
    assert not session(cookie,now=1001)


def test_empty_or_malformed_sessions_are_not_authenticated():
    assert not session('') and not session('a.b.c')


def test_team_api_requires_login_and_blocks_review_writes(monkeypatch):
    import asyncio
    import pytest
    from starlette.requests import Request
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse
    from app.team_api import authenticate,login,COOKIE
    from app.readonly_api import call_tool
    monkeypatch.setenv('TEAM_ACCESS_TOKEN','z'*40)
    def request(cookie=None):
        headers=[] if cookie is None else [(b'cookie',f'{COOKIE}={cookie}'.encode())]
        return Request({'type':'http','method':'GET','scheme':'http','path':'/api/health','query_string':b'',
                        'headers':headers,'server':('test',80),'root_path':''})
    async def next_handler(req):return JSONResponse({'ok':True})
    class LoginRequest:
        headers={}
        base_url='http://test/'
        def __init__(self,token):self.token=token
        async def form(self):return {'token':self.token}
    async def run():
        assert (await authenticate(request(),next_handler)).status_code==401
        assert (await authenticate(request(issue_session()),next_handler)).status_code==200
        with pytest.raises(HTTPException) as error:await call_tool('submit_review',None)
        assert error.value.status_code==403
        assert (await login(LoginRequest('bad'))).status_code==401
        valid=await login(LoginRequest('z'*40))
        assert valid.status_code==303
        assert 'HttpOnly' in valid.headers['set-cookie'] and 'SameSite=strict' in valid.headers['set-cookie']
        bearer=request();bearer.scope['headers']=[(b'authorization',b'Bearer '+b'z'*40)]
        assert (await authenticate(bearer,next_handler)).status_code==200
        invalid=request();invalid.scope['headers']=[(b'authorization',b'Bearer incorrect-key')]
        assert (await authenticate(invalid,next_handler)).status_code==401
    asyncio.run(run())
