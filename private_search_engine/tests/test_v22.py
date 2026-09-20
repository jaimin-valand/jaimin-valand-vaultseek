from private_search_engine.core.document import Document
from private_search_engine.distributed.sharded import ShardedSearchEngine

def docs(): return [Document('https://a/1','Python search','python search indexing architecture'),Document('https://a/2','Database systems','database indexing and storage'),Document('https://b/3','Private search','private search engine retrieval'),Document('https://b/4','Crawler','web crawler and robots'),Document('https://c/5','Hybrid retrieval','bm25 hybrid retrieval search')]

def test_stable_shard_assignment_and_distribution(tmp_path):
    engine=ShardedSearchEngine(3,tmp_path/'shards'); engine.add_many(docs()); assert engine.shard_for(docs()[0].doc_id)==engine.shard_for(docs()[0].doc_id); assert engine.stats()['documents']==5; assert sum(s['documents'] for s in engine.stats()['shards'])==5

def test_fanout_global_top_k(tmp_path):
    engine=ShardedSearchEngine(3,tmp_path/'shards'); engine.add_many(docs()); hits=engine.search('search',limit=3,hybrid=False); assert len(hits)==3; assert {h.doc_id for h in hits}.issubset({d.doc_id for d in docs()}); assert all(hits[i].score>=hits[i+1].score for i in range(len(hits)-1)); assert engine.report()['shards_queried']==3

def test_and_query_fans_out(tmp_path):
    engine=ShardedSearchEngine(4,tmp_path/'shards'); engine.add_many(docs()); hits=engine.search('python search',limit=10,mode='AND',hybrid=False); assert [h.title for h in hits]==['Python search']

def test_persistence_roundtrip(tmp_path):
    path=tmp_path/'shards'; first=ShardedSearchEngine(4,path); first.add_many(docs()); second=ShardedSearchEngine(4,path); assert second.stats()['documents']==5; assert second.search('private search',hybrid=False)[0].title=='Private search'

def test_invalid_configuration():
    try: ShardedSearchEngine(0); assert False
    except ValueError: pass
