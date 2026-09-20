from private_search_engine.core.document import Document
from private_search_engine.core.engine import SearchEngine
from private_search_engine.segments.store import SegmentStore
from private_search_engine.persistence.wal import WriteAheadLog

def test_segment_roundtrip_and_latest_doc_wins(tmp_path):
    store=SegmentStore(tmp_path/'segments'); a=Document('https://x/a','Old','old'); b=Document('https://x/b','B','b'); store.write_segment([a,b]); store.write_segment([Document('https://x/a','New','new')]); docs={d.doc_id:d for d in store.all_documents()}; assert docs[a.doc_id].title=='New' and len(docs)==2

def test_segment_compaction(tmp_path):
    store=SegmentStore(tmp_path/'segments'); store.write_segment([Document('https://x/a','A','a')]); store.write_segment([Document('https://x/b','B','b')]); assert store.compact() is True; assert len(store.list_segments())==1; assert len(store.all_documents())==2

def test_wal_recovery_replays_pending_upsert(tmp_path):
    wal=WriteAheadLog(tmp_path/'index.wal'); d=Document('https://x/recover','Recover','durable'); wal.append('upsert',d.to_dict()); engine=SearchEngine(store_path=tmp_path/'index.json',metadata_path=tmp_path/'search.db',wal_path=tmp_path/'index.wal',segment_path=tmp_path/'segments'); assert engine.wal_status()['recovered_records']==1; assert engine.search('durable',hybrid=False)[0].doc_id==d.doc_id
