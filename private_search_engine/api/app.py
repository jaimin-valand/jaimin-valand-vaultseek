from fastapi import FastAPI, Query, Request, Header, HTTPException
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from ..core.engine import SearchEngine
from ..benchmark.evaluator import load_cases, evaluate
from ..distributed.sharded import ShardedSearchEngine
from ..distributed.remote import RemoteShardCoordinator, RemoteShardNode
from ..observability import TraceStore
from ..config import settings
from ..security import RateLimiter, valid_api_key
from ..lifecycle import Lifecycle
import time, uuid

@asynccontextmanager
async def lifespan(_app):
    LIFECYCLE.ready=True; LIFECYCLE.draining=False
    yield
    LIFECYCLE.begin_shutdown()

app=FastAPI(title='Private Search Engine', version='3.0.0', description='Local-first private search platform with crawling, retrieval, distributed search, consensus, recovery, and observability.', lifespan=lifespan)
engine=SearchEngine(); TRACE_STORE=TraceStore(max_traces=settings.max_trace_limit); LIMITER=RateLimiter(settings.rate_limit_per_minute); LIFECYCLE=Lifecycle()

@app.middleware('http')
async def platform_middleware(request: Request, call_next):
    request_id=request.headers.get('X-Request-ID') or uuid.uuid4().hex
    if LIFECYCLE.draining: return JSONResponse(status_code=503, content={'error':'service draining','request_id':request_id})
    client=request.client.host if request.client else 'unknown'
    if not LIMITER.allow(client): return JSONResponse(status_code=429, content={'error':'rate limit exceeded','request_id':request_id})
    if request.method in {'POST','PUT','PATCH'}:
        length=request.headers.get('content-length')
        if length and int(length)>settings.max_body_bytes: return JSONResponse(status_code=413, content={'error':'request body too large','request_id':request_id})
    start=time.perf_counter()
    response=await call_next(request)
    response.headers['X-Request-ID']=request_id; response.headers['X-Processing-Time-Ms']=f'{(time.perf_counter()-start)*1000:.3f}'
    return response


def auth(x_api_key: str|None):
    if not valid_api_key(x_api_key, settings.api_key): raise HTTPException(status_code=401, detail='invalid API key')

@app.get('/health')
def health(): return {'status':'ok','version':'3.0.0','documents':len(engine.index.documents),'metadata_documents':engine.metadata.count(),'lifecycle':LIFECYCLE.status()}
@app.get('/ready')
def ready():
    if not LIFECYCLE.ready: raise HTTPException(status_code=503, detail='not ready')
    return {'status':'ready','version':'3.0.0'}
@app.get('/version')
def version(): return {'version':'3.0.0','environment':settings.environment}
@app.get('/search')
def search(q:str=Query(min_length=1), limit:int=Query(10,ge=1,le=100), domain:str|None=None, content_type:str|None=None, x_api_key:str|None=Header(default=None)):
    auth(x_api_key); return {'query':q,'results':[h.__dict__ for h in engine.search(q,limit,domain,content_type)]}
class CrawlRequest(BaseModel): seeds:list[str]=Field(min_length=1); max_pages:int=Field(default=25,ge=1,le=1000)
@app.post('/crawl')
def crawl(req:CrawlRequest,x_api_key:str|None=Header(default=None)):
    auth(x_api_key); docs=engine.crawl_and_index(req.seeds,req.max_pages); return {'indexed':len(docs),'documents':len(engine.index.documents)}
@app.get('/stats')
def stats(): return {'version':'3.0.0','documents':len(engine.index.documents),'metadata_documents':engine.metadata.count(),'wal':engine.wal_status(),'hybrid_retrieval':True,'compression':'variable-byte delta'}
@app.post('/benchmark')
def benchmark(dataset: str='examples/benchmark_cases.json',x_api_key:str|None=Header(default=None)): auth(x_api_key); return evaluate(engine,load_cases(dataset)).__dict__
class DistributedSearchRequest(BaseModel): q:str=Field(min_length=1); limit:int=Field(default=10,ge=1,le=100); shards:int=Field(default=4,ge=1,le=64); mode:str=Field(default='OR')
@app.post('/distributed/search')
def distributed_search(req:DistributedSearchRequest,x_api_key:str|None=Header(default=None)):
    auth(x_api_key); hits,cluster=engine.sharded_search(req.q,req.limit,mode=req.mode,shard_count=req.shards); return {'query':req.q,'results':[h.__dict__ for h in hits],'report':cluster.report(),'stats':cluster.stats()}
@app.get('/distributed/stats')
def distributed_stats(shards:int=Query(4,ge=1,le=64)): cluster=ShardedSearchEngine(shard_count=shards); cluster.add_many(engine.index.documents.values()); return cluster.stats()
class RemoteSearchRequest(BaseModel): q:str=Field(min_length=1); nodes:list[str]=Field(min_length=1); limit:int=Field(default=10,ge=1,le=100); mode:str=Field(default='OR')
@app.post('/remote/search')
def remote_search(req:RemoteSearchRequest,x_api_key:str|None=Header(default=None)):
    auth(x_api_key); nodes=req.nodes[:settings.max_remote_nodes]; coordinator=RemoteShardCoordinator([RemoteShardNode(f'shard-{i}',url) for i,url in enumerate(nodes)],trace_store=TRACE_STORE); results=coordinator.search(req.q,req.limit,mode=req.mode); return {'query':req.q,'results':results,'report':coordinator.report(),'health':coordinator.health()}
@app.get('/remote/health')
def remote_health(nodes:list[str]=Query(min_length=1)): return {'nodes':RemoteShardCoordinator([RemoteShardNode(f'shard-{i}',url) for i,url in enumerate(nodes[:settings.max_remote_nodes])]).health()}
@app.get('/observability/traces')
def observability_traces(limit:int=Query(50,ge=1,le=settings.max_trace_limit)): return {'traces':TRACE_STORE.traces()[:limit]}
@app.get('/observability/traces/{trace_id}')
def observability_trace(trace_id:str): return TRACE_STORE.get(trace_id) or {'error':'trace not found'}
@app.get('/observability/metrics')
def observability_metrics(): return TRACE_STORE.metrics()
