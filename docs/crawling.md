# Crawling

Private Search Engine 1.4 introduces a production-oriented crawl frontier with:

- `robots.txt` compliance by default
- configurable per-domain crawl delay
- bounded concurrent workers
- retry/backoff for transient HTTP failures
- URL de-fragmentation and same-host frontier expansion
- a descriptive User-Agent
- crawl statistics for fetched, blocked, retried and failed requests

The crawler intentionally remains bounded by `max_pages` and does not bypass robots rules. `respect_robots=False` is available for controlled local tests only.
