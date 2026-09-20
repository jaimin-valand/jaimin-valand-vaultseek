from __future__ import annotations
import concurrent.futures, time, statistics
from urllib.request import Request, urlopen
from urllib.parse import quote

def run(url: str, requests: int = 50, concurrency: int = 10, query: str = 'python') -> dict:
    requests, concurrency = max(1, requests), max(1, min(concurrency, requests))
    def one(_):
        start=time.perf_counter(); status=0
        try:
            req=Request(url + '?q=' + quote(query), headers={'User-Agent':'PrivateSearchEngineLoadTest/3.0'})
            with urlopen(req, timeout=10) as r: r.read(); status=r.status
        except Exception: status=0
        return (time.perf_counter()-start)*1000, status
    started=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        results=list(pool.map(one, range(requests)))
    lat=[x[0] for x in results]; ok=sum(x[1]==200 for x in results)
    ordered=sorted(lat); p95=ordered[min(len(ordered)-1, max(0,int(len(ordered)*.95)-1))]
    return {'requests':requests,'concurrency':concurrency,'successful':ok,'failed':requests-ok,'success_rate':ok/requests,'avg_latency_ms':statistics.mean(lat),'p95_latency_ms':p95,'max_latency_ms':max(lat),'elapsed_ms':(time.perf_counter()-started)*1000}
