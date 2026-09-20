from __future__ import annotations
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json, time
from threading import RLock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterable
from ..core.document import Document
from .sharded import ShardedSearchEngine
from ..observability import SearchTrace, TraceStore
@dataclass
class RemoteShardHealth:
    node_id:str; url:str; healthy:bool; failures:int; circuit_open:bool; last_error:str|None=None; latency_ms:float=0.0
    def to_dict(self): return asdict(self)
@dataclass
class RemoteSearchReport:
    query:str; nodes_total:int; nodes_healthy:int; nodes_queried:int; nodes_failed:int; partial:bool; candidate_hits:int; returned_hits:int; elapsed_ms:float
    def to_dict(self): return asdict(self)
class CircuitBreaker:
    def __init__(self,failure_threshold=3,reset_timeout=10.0):
        if failure_threshold<1: raise ValueError('failure_threshold must be >= 1')
        self.failure_threshold=failure_threshold; self.reset_timeout=reset_timeout; self.failures=0; self.opened_at=0.0
    @property
    def open(self): return self.failures>=self.failure_threshold and (time.monotonic()-self.opened_at)<self.reset_timeout
    def allow(self):
        if self.failures<self.failure_threshold:return True
        if time.monotonic()-self.opened_at>=self.reset_timeout:self.failures=0;self.opened_at=0.0;return True
        return False
    def success(self): self.failures=0;self.opened_at=0.0
    def failure(self):
        self.failures+=1
        if self.failures>=self.failure_threshold:self.opened_at=time.monotonic()
@dataclass
class RemoteShardNode:
    node_id:str; url:str; timeout:float=1.5; retries:int=1; failure_threshold:int=3; reset_timeout:float=10.0
    def __post_init__(self): self.url=self.url.rstrip('/'); self.breaker=CircuitBreaker(self.failure_threshold,self.reset_timeout); self.last_error=None; self.last_latency_ms=0.0; self._lock=RLock()
    def _request(self,method,path,payload=None):
        body=None if payload is None else json.dumps(payload,separators=(',',':')).encode(); headers={'Accept':'application/json'}
        if body is not None: headers['Content-Type']='application/json'
        started=time.perf_counter(); request=Request(self.url+path,data=body,headers=headers,method=method)
        with urlopen(request,timeout=self.timeout) as response: raw=response.read()
        self.last_latency_ms=round((time.perf_counter()-started)*1000,4); return json.loads(raw.decode('utf-8'))
    def health(self):
        if not self.breaker.allow():return False
        try:self._request('GET','/health');self.breaker.success();self.last_error=None;return True
        except Exception as exc:self.breaker.failure();self.last_error=f'{type(exc).__name__}: {exc}';return False
    def load(self,documents):
        docs=[d.to_dict() for d in documents]
        if not docs:return {'accepted':0}
        try:result=self._request('POST','/documents',{'documents':docs});self.breaker.success();self.last_error=None;return result
        except Exception as exc:self.breaker.failure();self.last_error=f'{type(exc).__name__}: {exc}';raise
    def search(self,query,limit,domain=None,content_type=None,mode='OR',hybrid=True):
        if not self.breaker.allow():raise RuntimeError('circuit open')
        payload={'q':query,'limit':limit,'domain':domain,'content_type':content_type,'mode':mode,'hybrid':hybrid}; last=None
        for attempt in range(self.retries+1):
            try:result=self._request('POST','/search',payload);self.breaker.success();self.last_error=None;return result
            except (HTTPError,URLError,TimeoutError,OSError,ValueError,RuntimeError) as exc:
                last=exc;self.breaker.failure();self.last_error=f'{type(exc).__name__}: {exc}'
                if attempt<self.retries: time.sleep(0.03*(2**attempt))
        raise RuntimeError(str(last))
    def status(self): return RemoteShardHealth(self.node_id,self.url,self.health(),self.breaker.failures,self.breaker.open,self.last_error,self.last_latency_ms).to_dict()
class RemoteShardCoordinator:
    """Coordinator for remote shard nodes with retries and circuit breaking."""
    def __init__(self,nodes,max_workers=None,trace_store=None):
        self.nodes=list(nodes)
        if not self.nodes:raise ValueError('at least one remote shard node is required')
        self.max_workers=max_workers or len(self.nodes);self._lock=RLock();self.trace_store=trace_store or TraceStore();self.last_trace=None;self.last_report=RemoteSearchReport('',len(self.nodes),0,0,0,False,0,0,0.0)
    def _merge(self,hits,limit): return sorted(hits,key=lambda h:(-float(h.get('score',0.0)),h.get('doc_id','')))[:limit]
    def search(self,query,limit=10,domain=None,content_type=None,mode='OR',hybrid=True):
        if limit<1 or limit>1000:raise ValueError('limit must be between 1 and 1000')
        started=time.perf_counter();trace=SearchTrace();healthy=[n for n in self.nodes if n.breaker.allow()];results=[];failed=0;queried=0
        def run(node):
            try:
                with trace.span('shard.search',node_id=node.node_id,query=query,limit=limit): result=node.search(query,min(max(limit*3,limit),1000),domain,content_type,mode,hybrid); return node,result,None
            except Exception as exc:return node,None,exc
        with trace.span('query.fanout',shard_count=len(healthy),requested_shards=len(self.nodes)):
            with ThreadPoolExecutor(max_workers=min(self.max_workers,len(healthy) or 1)) as pool:
                for node,result,error in pool.map(run,healthy):
                    queried+=1
                    if error is not None:failed+=1
                    else:results.extend(result.get('results',[]))
        with trace.span('result.merge',candidate_hits=len(results),limit=limit): merged=self._merge(results,limit)
        elapsed=round((time.perf_counter()-started)*1000,4); self.last_trace=trace;self.trace_store.add(trace)
        self.last_report=RemoteSearchReport(query,len(self.nodes),len(healthy),queried,failed,failed>0,len(results),len(merged),elapsed);return merged
    def health(self): return [node.status() for node in self.nodes]
    def report(self):
        report=self.last_report.to_dict();report['trace_id']=self.last_trace.trace_id if self.last_trace else None;return report
    def traces(self):return self.trace_store.traces()
    def trace(self,trace_id):return self.trace_store.get(trace_id)
    def load_documents(self,documents):
        docs=list(documents)
        for doc in docs:
            index=int.from_bytes(sha256(doc.doc_id.encode()).digest()[:8],'big')%len(self.nodes);self.nodes[index].load([doc])
class ShardNodeServer:
    def __init__(self,host='127.0.0.1',port=0,node_id='shard-0',shard_engine=None):
        self.engine=shard_engine or ShardedSearchEngine(shard_count=1);self.node_id=node_id;engine=self.engine
        class Handler(BaseHTTPRequestHandler):
            def _json(self,status,payload):
                raw=json.dumps(payload,separators=(',',':')).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def _body(self):
                length=int(self.headers.get('Content-Length','0'));return json.loads(self.rfile.read(length).decode('utf-8')) if length else {}
            def do_GET(self):
                if self.path=='/health':self._json(200,{'status':'ok','node_id':self.server.node_id,'documents':len(engine.shards[0].documents)})
                elif self.path=='/stats':self._json(200,engine.stats())
                else:self._json(404,{'error':'not found'})
            def do_POST(self):
                try:
                    body=self._body()
                    if self.path=='/documents':
                        accepted=0
                        for item in body.get('documents',[]):engine.add(Document(item['url'],item['title'],item['text'],item.get('content_type','text/html')));accepted+=1
                        self._json(200,{'accepted':accepted})
                    elif self.path=='/search':
                        hits=engine.search(body.get('q',''),int(body.get('limit',10)),body.get('domain'),body.get('content_type'),body.get('mode','OR'),bool(body.get('hybrid',True)));self._json(200,{'results':[h.__dict__ for h in hits],'node_id':self.server.node_id})
                    else:self._json(404,{'error':'not found'})
                except Exception as exc:self._json(400,{'error':f'{type(exc).__name__}: {exc}'})
            def log_message(self,fmt,*args):return
        self.server=ThreadingHTTPServer((host,port),Handler);self.server.node_id=node_id
    @property
    def address(self):host,port=self.server.server_address;return f'http://{host}:{port}'
    def serve_forever(self):self.server.serve_forever()
    def shutdown(self):self.server.shutdown();self.server.server_close()
