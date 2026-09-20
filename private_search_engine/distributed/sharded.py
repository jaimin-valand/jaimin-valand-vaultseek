from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from pathlib import Path
from threading import RLock
from typing import Iterable
from ..core.document import Document
from ..core.index import InvertedIndex, SearchHit
from ..retrieval.hybrid import HybridRanker
@dataclass(frozen=True)
class ShardSearchReport:
    query:str; shard_count:int; shards_queried:int; candidate_hits:int; returned_hits:int; elapsed_ms:float; mode:str
    def to_dict(self): return asdict(self)
class ShardedSearchEngine:
    """Deterministic local simulation of a horizontally sharded search cluster."""
    def __init__(self,shard_count=4,storage_path=None,max_workers=None):
        if shard_count<1 or shard_count>64: raise ValueError('shard_count must be between 1 and 64')
        self.shard_count=shard_count; self.shards=[InvertedIndex() for _ in range(shard_count)]; self.hybrid=HybridRanker(); self.storage_path=Path(storage_path) if storage_path else None; self.max_workers=max_workers or shard_count; self._lock=RLock()
        if self.storage_path: self.storage_path.mkdir(parents=True,exist_ok=True); self._load()
    def shard_for(self,doc_id): return int.from_bytes(sha256(doc_id.encode('utf-8')).digest()[:8],'big')%self.shard_count
    def add(self,doc):
        with self._lock: self.shards[self.shard_for(doc.doc_id)].add(doc)
    def add_many(self,docs):
        for doc in docs: self.add(doc)
        if self.storage_path: self.persist()
    def persist(self):
        if not self.storage_path:return
        with self._lock:
            for i,shard in enumerate(self.shards):
                payload=[d.to_dict() for d in sorted(shard.documents.values(),key=lambda d:d.doc_id)]; target=self.storage_path/f'shard-{i}.json'; tmp=target.with_suffix('.tmp'); tmp.write_text(json.dumps(payload,separators=(',',':'),sort_keys=True),encoding='utf-8'); tmp.replace(target)
    def _load(self):
        for i,shard in enumerate(self.shards):
            path=self.storage_path/f'shard-{i}.json'
            if not path.exists(): continue
            try: payload=json.loads(path.read_text(encoding='utf-8'))
            except (OSError,json.JSONDecodeError): continue
            for item in payload: shard.add(Document(item['url'],item['title'],item['text'],item.get('content_type','text/html')))
    def _search_shard(self,shard_id,query,limit,domain,content_type,mode):
        shard=self.shards[shard_id]; hits=shard.search(query,limit=limit,domain=domain,content_type=content_type,mode=mode); return self.hybrid.rerank(query,hits,shard.documents) if hits else []
    @staticmethod
    def _merge(hits,limit): return sorted(hits,key=lambda h:(-h.score,h.doc_id))[:limit]
    def search(self,query,limit=10,domain=None,content_type=None,mode='OR',hybrid=True):
        import time
        if limit<1 or limit>1000: raise ValueError('limit must be between 1 and 1000')
        if mode.upper() not in {'OR','AND'}: raise ValueError('mode must be AND or OR')
        started=time.perf_counter(); per_shard_limit=min(max(limit*3,limit),1000)
        with ThreadPoolExecutor(max_workers=min(self.max_workers,self.shard_count)) as pool:
            futures=[pool.submit(self._search_shard,i,query,per_shard_limit,domain,content_type,mode.upper()) for i in range(self.shard_count)]; shard_hits=[f.result() for f in futures]
        flattened=[hit for hits in shard_hits for hit in hits]; merged=self._merge(flattened,limit); elapsed=(time.perf_counter()-started)*1000
        self.last_report=ShardSearchReport(query,self.shard_count,self.shard_count,len(flattened),len(merged),round(elapsed,4),mode.upper()); return merged
    def stats(self):
        rows=[]
        for i,shard in enumerate(self.shards): rows.append({'shard_id':i,'documents':len(shard.documents),'terms':len(shard.postings),'avg_document_length':round(sum(shard.doc_lengths.values())/max(len(shard.documents),1),3)})
        return {'shard_count':self.shard_count,'documents':sum(x['documents'] for x in rows),'shards':rows}
    def report(self): return getattr(self,'last_report',ShardSearchReport('',self.shard_count,0,0,0,0.0,'OR')).to_dict()
