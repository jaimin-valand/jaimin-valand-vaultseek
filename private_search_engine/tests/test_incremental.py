from private_search_engine.core.document import Document
from private_search_engine.storage.sqlite_store import SQLiteStore

def test_content_hash_is_stable():
    a=Document('https://a.test','A','hello'); b=Document('https://a.test','A','hello'); assert a.content_hash==b.content_hash

def test_sqlite_metadata_round_trip(tmp_path):
    store=SQLiteStore(tmp_path/'search.db'); doc=Document('https://a.test','A','hello'); store.upsert(doc,etag='abc',last_modified='today'); row=store.get_by_url(doc.url); assert row['etag']=='abc'; assert store.count()==1; assert store.all_documents()[0].url==doc.url
