from private_search_engine.core.engine import SearchEngine
from private_search_engine.core.document import Document
from private_search_engine.benchmark.evaluator import BenchmarkCase, evaluate

def test_benchmark_metrics(tmp_path):
    e=SearchEngine(str(tmp_path/'index.json'), str(tmp_path/'search.db'))
    docs=[Document('https://example.test/private','Private Search','private search engine'),Document('https://example.test/ml','Machine Learning','machine learning systems')]
    for d in docs: e.index.add(d)
    report=evaluate(e,[BenchmarkCase('private search',[docs[0].doc_id]),BenchmarkCase('machine learning',[docs[1].doc_id])])
    assert report.cases==2; assert report.precision_at_k>0; assert report.mrr==1.0; assert report.ndcg_at_k==1.0; assert report.max_latency_ms>=0
