from dataclasses import replace

def test_platform_endpoints_and_headers():
    from fastapi.testclient import TestClient
    from private_search_engine.api import app as mod
    original=mod.settings; mod.settings=replace(original,api_key='secret')
    try:
        with TestClient(mod.app) as c:
            r=c.get('/health'); assert r.status_code==200 and r.headers['X-Request-ID']; assert c.get('/ready').status_code==200; assert c.get('/version').json()['version']=='3.0.0'; assert c.get('/search?q=test').status_code==401; assert c.get('/search?q=test',headers={'X-API-Key':'secret'}).status_code==200
    finally: mod.settings=original

def test_constant_time_auth():
    from private_search_engine.security import valid_api_key
    assert valid_api_key('abc','abc'); assert not valid_api_key('abd','abc'); assert valid_api_key(None,'')

def test_rate_limiter():
    from private_search_engine.security import RateLimiter
    r=RateLimiter(2,60); assert r.allow('x'); assert r.allow('x'); assert not r.allow('x')

def test_loadtest_report_shape():
    from private_search_engine.loadtest import run
    assert callable(run)
