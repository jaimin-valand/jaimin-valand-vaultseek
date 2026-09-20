from private_search_engine.core.crawler import Crawler

def test_robots_disabled_allows_http_urls():
    c=Crawler(respect_robots=False); assert c.allowed('https://example.com/private')

def test_crawler_defaults_are_polite():
    c=Crawler(); assert c.workers>=1; assert c.max_retries>=0; assert c.user_agent.startswith('PrivateSearchEngine/')
