from private_search_engine.core.crawler import CrawlStats

def test_stats_shape():
    s=CrawlStats(); s.pages_indexed=2; s.retries=1; assert s.pages_indexed==2 and s.retries==1
