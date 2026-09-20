from .index import InvertedIndex
from .crawler import Crawler
from ..storage.store import JsonStore
from ..storage.sqlite_store import SQLiteStore
from ..persistence.wal import WriteAheadLog
from ..segments.store import SegmentStore
from ..retrieval.hybrid import HybridRanker
from .document import Document

class SearchEngine:
    def __init__(self, store_path='data/index.json', metadata_path='data/search.db', wal_path='data/index.wal', segment_path='data/segments'):
        self.index=InvertedIndex(); self.store=JsonStore(store_path); self.metadata=SQLiteStore(metadata_path)
        self.wal=WriteAheadLog(wal_path); self.segments=SegmentStore(segment_path); self.hybrid=HybridRanker(); self._load()

    def _load(self):
        docs = self.segments.all_documents() if self.segments.list_segments() else (self.metadata.all_documents() if self.metadata.count() else self.store.load())
        for d in docs: self.index.add(d)
        recovered = 0
        for record in self.wal.records():
            if record.get('operation') == 'upsert' and record.get('payload'):
                d = record['payload']; doc=Document(d['url'],d['title'],d['text'],d.get('content_type','text/html')); self.index.add(doc); recovered += 1
        self._recovered_records = recovered

    def index_documents(self, docs):
        batch=[]
        for d in docs:
            self.wal.append('upsert', d.to_dict()); self.index.add(d); self.metadata.upsert(d); batch.append(d)
        if batch:
            self.segments.write_segment(batch)
            self.store.save(self.index.documents.values()); self.wal.checkpoint()

    def compact_segments(self):
        return self.segments.compact()

    def search(self, query, limit=10, domain=None, content_type=None, mode='OR', hybrid=True):
        hits=self.index.search(query, limit=max(limit, limit*2), domain=domain, content_type=content_type, mode=mode)
        return self.hybrid.rerank(query, hits, self.index.documents)[:limit] if hybrid and hits else hits

    def wal_status(self):
        return {'path': str(self.wal.path), 'pending_records': len(self.wal.records()), 'recovered_records': self._recovered_records}

    def segment_status(self):
        return {'segments': self.segments.list_segments(), 'count': len(self.segments.list_segments())}

    def crawl_and_index(self,seeds,max_pages=25):
        crawler=Crawler(max_pages=max_pages); docs=[]; queue=list(seeds); seen=set()
        while queue and len(seen)<max_pages:
            url=queue.pop(0)
            if url in seen: continue
            seen.add(url); old=self.metadata.get_by_url(url)
            r=crawler.fetch(url, etag=old['etag'] if old else None, last_modified=old['last_modified'] if old else None)
            if r.not_modified or not r.document: continue
            docs.append(r.document); self.wal.append('upsert', r.document.to_dict()); self.index.add(r.document); self.metadata.upsert(r.document,etag=r.etag,last_modified=r.last_modified)
            from urllib.parse import urljoin, urlparse
            for link in r.links:
                absolute=urljoin(url,link).split('#')[0]
                if urlparse(absolute).netloc==urlparse(url).netloc and absolute not in seen: queue.append(absolute)
        if docs:
            self.segments.write_segment(docs); self.store.save(self.index.documents.values()); self.wal.checkpoint()
        return docs

    def sharded_search(self, query, limit=10, domain=None, content_type=None, mode='OR', shard_count=4):
        from ..distributed.sharded import ShardedSearchEngine
        cluster = ShardedSearchEngine(shard_count=shard_count)
        cluster.add_many(self.index.documents.values())
        return cluster.search(query, limit, domain, content_type, mode, hybrid=True), cluster
