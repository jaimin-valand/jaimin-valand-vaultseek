from private_search_engine.core.document import Document
from private_search_engine.core.index import InvertedIndex, QueryParser

def build_index():
    index=InvertedIndex(); index.add(Document('https://a.test/1','Private Search','Python makes private search systems practical. Machine learning improves ranking.')); index.add(Document('https://a.test/2','Search Notes','Private search systems can run locally without machine learning.')); index.add(Document('https://a.test/3','Cooking','Tomatoes and pasta are useful ingredients.')); return index

def test_query_parser_extracts_phrases():
    parsed=QueryParser.parse('"private search" ranking'); assert parsed.phrases==[['private','search']]; assert parsed.terms==['ranking']

def test_exact_phrase_ranks_matching_document():
    results=build_index().search('"private search"'); assert results; assert results[0].url.endswith('/1')

def test_and_mode_requires_all_terms():
    results=build_index().search('private ranking',mode='AND'); assert len(results)==1; assert results[0].url.endswith('/1')

def test_title_field_boost():
    index=InvertedIndex(); index.add(Document('https://a.test/title','Python Search','unrelated text')); index.add(Document('https://a.test/body','Other','Python search appears in the body.')); results=index.search('python search'); assert results[0].url.endswith('/title')
