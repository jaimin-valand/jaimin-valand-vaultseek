from private_search_engine.core.document import Document
from private_search_engine.core.index import InvertedIndex

def test_bm25_ranking_and_snippet():
 i=InvertedIndex(); i.add(Document('https://a.test/1','Python Search','Python is a private search engine.')); i.add(Document('https://a.test/2','Cooking','Pasta and tomatoes.')); r=i.search('private search'); assert r[0].url.endswith('/1'); assert 'private' in r[0].snippet.lower()

def test_domain_filter():
 i=InvertedIndex(); i.add(Document('https://one.example/a','A','database')); i.add(Document('https://two.test/b','B','database')); assert len(i.search('database',domain='test'))==1

def test_content_filter():
 i=InvertedIndex(); i.add(Document('https://a.test/a','A','database','text/html')); i.add(Document('https://a.test/b','B','database','text/plain')); assert len(i.search('database',content_type='text/plain'))==1
