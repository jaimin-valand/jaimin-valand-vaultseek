from private_search_engine.core.document import Document
from private_search_engine.core.index import InvertedIndex
from private_search_engine.retrieval.compression import encode_delta, decode_delta
from private_search_engine.retrieval.hybrid import HybridRanker
from private_search_engine.persistence.wal import WriteAheadLog

def test_delta_compression_roundtrip():
    ids=[1,2,9,20,21]; assert decode_delta(encode_delta(ids))==ids

def test_hybrid_ranker_is_deterministic():
    idx=InvertedIndex(); docs=[Document('https://x/a','Python Search','python retrieval engine'),Document('https://x/b','Cooking','pasta recipe')]
    for d in docs: idx.add(d)
    hits=idx.search('python search',10); r=HybridRanker().rerank('python search',hits,idx.documents); assert r and r[0].doc_id==docs[0].doc_id

def test_wal_append_and_checkpoint(tmp_path):
    wal=WriteAheadLog(tmp_path/'x.wal'); wal.append('upsert',{'doc_id':'1'}); assert len(wal.records())==1; wal.checkpoint(); assert wal.records()==[]
