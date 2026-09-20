from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from html.parser import HTMLParser
from time import monotonic, sleep
from urllib.error import HTTPError
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from threading import Lock
import random

from .document import Document


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title: list[str] = []
        self.text: list[str] = []
        self.links: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "title": self.in_title = True
        if tag.lower() == "a" and attrs.get("href"): self.links.append(attrs["href"])

    def handle_endtag(self, tag):
        if tag.lower() == "title": self.in_title = False

    def handle_data(self, data):
        if self.in_title: self.title.append(data)
        self.text.append(data)


@dataclass
class FetchResult:
    url: str
    document: Document | None = None
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False
    error: str | None = None
    links: list[str] = field(default_factory=list)
    status_code: int | None = None


@dataclass
class CrawlStats:
    requested: int = 0
    fetched: int = 0
    not_modified: int = 0
    blocked_robots: int = 0
    skipped_scheme: int = 0
    skipped_duplicate: int = 0
    errors: int = 0
    unsupported: int = 0
    retries: int = 0
    pages_indexed: int = 0
    elapsed_ms: float = 0.0


class _DomainLimiter:
    def __init__(self, delay: float):
        self.delay = max(0.0, delay)
        self._last: dict[str, float] = {}
        self._lock = Lock()

    def wait(self, domain: str):
        if self.delay <= 0: return
        with self._lock:
            now = monotonic(); last = self._last.get(domain, 0.0)
            wait = self.delay - (now - last)
            if wait > 0: sleep(wait)
            self._last[domain] = monotonic()


class Crawler:
    """Polite concurrent crawler with robots.txt, retries and per-domain throttling."""
    def __init__(self, max_pages=50, timeout=5, workers=4, crawl_delay=0.0,
                 respect_robots=True, max_retries=2, backoff_base=0.25,
                 user_agent='PrivateSearchEngine/1.4'):
        self.max_pages = max_pages
        self.timeout = timeout
        self.workers = max(1, workers)
        self.crawl_delay = max(0.0, crawl_delay)
        self.respect_robots = respect_robots
        self.max_retries = max(0, max_retries)
        self.backoff_base = max(0.0, backoff_base)
        self.user_agent = user_agent
        self.stats = CrawlStats()
        self._robots: dict[str, RobotFileParser] = {}
        self._robots_lock = Lock()
        self._limiters: dict[str, _DomainLimiter] = {}

    def _robots_for(self, url: str):
        p = urlparse(url); base = f'{p.scheme}://{p.netloc}'
        with self._robots_lock:
            if base in self._robots: return self._robots[base]
        rp = RobotFileParser(); rp.set_url(urljoin(base + '/', 'robots.txt'))
        try: rp.read()
        except Exception: rp.parse(['User-agent: *', 'Allow: /'])
        with self._robots_lock:
            self._robots[base] = rp
        return rp

    def allowed(self, url: str) -> bool:
        return (not self.respect_robots) or self._robots_for(url).can_fetch(self.user_agent, url)

    def _limiter(self, domain):
        with self._robots_lock:
            return self._limiters.setdefault(domain, _DomainLimiter(self.crawl_delay))

    def fetch(self, url, *, etag=None, last_modified=None):
        headers={'User-Agent': self.user_agent, 'Accept': 'text/html,application/xhtml+xml;q=0.9'}
        if etag: headers['If-None-Match']=etag
        if last_modified: headers['If-Modified-Since']=last_modified
        domain = urlparse(url).netloc
        self._limiter(domain).wait(domain)
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                self.stats.requested += 1
                req=Request(url, headers=headers)
                with urlopen(req, timeout=self.timeout) as r:
                    ctype=r.headers.get_content_type()
                    if ctype != 'text/html':
                        self.stats.unsupported += 1
                        return FetchResult(url, error=f'unsupported content type: {ctype}', status_code=getattr(r,'status',None))
                    raw=r.read(1_000_000)
                    p=_Parser(); p.feed(raw.decode('utf-8','ignore'))
                    doc=Document(url,' '.join(p.title).strip() or url,' '.join(p.text),ctype)
                    self.stats.fetched += 1
                    return FetchResult(url,doc,r.headers.get('ETag'),r.headers.get('Last-Modified'),links=p.links,status_code=getattr(r,'status',None))
            except HTTPError as e:
                if e.code == 304:
                    self.stats.not_modified += 1
                    return FetchResult(url,not_modified=True,etag=etag,last_modified=last_modified,status_code=304)
                if e.code in {429,500,502,503,504} and attempt < self.max_retries:
                    self.stats.retries += 1; sleep(self.backoff_base * (2 ** attempt) + random.random()*0.05); continue
                last_error=f'HTTP {e.code}'
                break
            except Exception as e:
                last_error=str(e)
                if attempt < self.max_retries:
                    self.stats.retries += 1; sleep(self.backoff_base * (2 ** attempt) + random.random()*0.05); continue
                break
        self.stats.errors += 1
        return FetchResult(url,error=last_error)

    def crawl(self, seeds):
        started=monotonic(); docs=[]; queue=[]; queued=set(); seen=set()
        for u in seeds:
            u=urldefrag(u)[0]
            if u not in queued: queue.append(u); queued.add(u)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            while queue and len(docs) < self.max_pages:
                batch=[]
                while queue and len(batch) < self.workers and len(docs)+len(batch) < self.max_pages:
                    url=queue.pop(0)
                    p=urlparse(url)
                    if p.scheme not in {'http','https'}: self.stats.skipped_scheme += 1; continue
                    if url in seen: self.stats.skipped_duplicate += 1; continue
                    seen.add(url)
                    if not self.allowed(url): self.stats.blocked_robots += 1; continue
                    batch.append(pool.submit(self.fetch,url))
                for future in as_completed(batch):
                    result=future.result()
                    if not result.document: continue
                    docs.append(result.document); self.stats.pages_indexed += 1
                    source_domain=urlparse(result.url).netloc
                    for link in result.links:
                        absolute=urldefrag(urljoin(result.url,link))[0]
                        if urlparse(absolute).netloc == source_domain and absolute not in seen and absolute not in queued:
                            queue.append(absolute); queued.add(absolute)
        self.stats.elapsed_ms=(monotonic()-started)*1000
        return docs
