import argparse
from .core.engine import SearchEngine
from .benchmark.evaluator import load_cases, evaluate, save_report
from .core.crawler import Crawler
from .distributed.sharded import ShardedSearchEngine
from .distributed.remote import RemoteShardCoordinator, RemoteShardNode, ShardNodeServer
from .loadtest import run as run_loadtest
from .release_gate import main as release_gate

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('search'); s.add_argument('query'); s.add_argument('--limit',type=int,default=10); s.add_argument('--mode',choices=['OR','AND'],default='OR')
    b=sub.add_parser('benchmark'); b.add_argument('dataset'); b.add_argument('--output',default='data/benchmark-report.json')
    d=sub.add_parser('distributed-search'); d.add_argument('query'); d.add_argument('--limit',type=int,default=10); d.add_argument('--shards',type=int,default=4); d.add_argument('--mode',choices=['OR','AND'],default='OR')
    r=sub.add_parser('remote-search'); r.add_argument('query'); r.add_argument('--nodes', nargs='+', required=True); r.add_argument('--limit', type=int, default=10); r.add_argument('--mode', choices=['OR','AND'], default='OR')
    n=sub.add_parser('remote-node'); n.add_argument('--host', default='127.0.0.1'); n.add_argument('--port', type=int, default=8001); n.add_argument('--node-id', default='shard-0')
    l=sub.add_parser('load-test'); l.add_argument('url'); l.add_argument('--requests',type=int,default=50); l.add_argument('--concurrency',type=int,default=10); l.add_argument('--query',default='python')
    g=sub.add_parser('release-gate')
    c=sub.add_parser('crawl'); c.add_argument('seeds',nargs='+'); c.add_argument('--max-pages',type=int,default=20); c.add_argument('--workers',type=int,default=4); c.add_argument('--delay',type=float,default=0.0); c.add_argument('--ignore-robots',action='store_true')
    a=p.parse_args(); engine=SearchEngine()
    if a.cmd=='search':
        for h in engine.search(a.query,a.limit,mode=a.mode): print(f'{h.score:.5f}\t{h.title}\t{h.url}')
    elif a.cmd=='distributed-search':
        cluster=ShardedSearchEngine(shard_count=a.shards); cluster.add_many(engine.index.documents.values()); hits=cluster.search(a.query,a.limit,mode=a.mode)
        for h in hits: print(f'{h.score:.5f}\t{h.title}\t{h.url}')
        print(f'shards={cluster.shard_count} candidates={cluster.report()["candidate_hits"]} elapsed_ms={cluster.report()["elapsed_ms"]}')
    elif a.cmd=='remote-search':
        cluster=RemoteShardCoordinator([RemoteShardNode(f'shard-{i}', url) for i, url in enumerate(a.nodes)])
        hits=cluster.search(a.query,a.limit,mode=a.mode)
        for h in hits: print(f'{float(h["score"]):.5f}\t{h.get("title","")}\t{h.get("url","")}')
        report=cluster.report(); print(f'nodes={report["nodes_total"]} failed={report["nodes_failed"]} partial={report["partial"]} elapsed_ms={report["elapsed_ms"]} trace_id={report["trace_id"]}')
    elif a.cmd=='remote-node':
        server=ShardNodeServer(a.host,a.port,a.node_id)
        print(f'listening={server.address} node={a.node_id}')
        server.serve_forever()
    elif a.cmd=='load-test':
        print(run_loadtest(a.url,a.requests,a.concurrency,a.query))
    elif a.cmd=='release-gate':
        raise SystemExit(release_gate())
    elif a.cmd=='benchmark':
        report=evaluate(engine,load_cases(a.dataset)); save_report(report,a.output)
        print(f'cases={report.cases} precision@k={report.precision_at_k:.3f} recall@k={report.recall_at_k:.3f} mrr={report.mrr:.3f} ndcg@k={report.ndcg_at_k:.3f} avg_ms={report.avg_latency_ms:.3f} p95_ms={report.p95_latency_ms:.3f}')
    else:
        crawler=Crawler(max_pages=a.max_pages,workers=a.workers,crawl_delay=a.delay,respect_robots=not a.ignore_robots)
        docs=crawler.crawl(a.seeds)
        print(f'pages={len(docs)} fetched={crawler.stats.fetched} blocked={crawler.stats.blocked_robots} retries={crawler.stats.retries} errors={crawler.stats.errors} elapsed_ms={crawler.stats.elapsed_ms:.2f}')
if __name__=='__main__': main()
