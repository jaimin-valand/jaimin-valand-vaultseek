from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json, math, time
from ..core.engine import SearchEngine

@dataclass(frozen=True)
class BenchmarkCase:
    query: str
    relevant: list[str]
    mode: str = 'OR'
    k: int = 5

@dataclass
class BenchmarkReport:
    cases: int
    precision_at_k: float
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    avg_latency_ms: float
    p95_latency_ms: float
    max_latency_ms: float
    per_query: list[dict]


def load_cases(path: str | Path) -> list[BenchmarkCase]:
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    return [BenchmarkCase(**x) for x in raw]


def _dcg(ids, relevant, k):
    score = 0.0
    for i, doc_id in enumerate(ids[:k], 1):
        if doc_id in relevant:
            score += 1.0 / math.log2(i + 1)
    return score


def evaluate(engine: SearchEngine, cases: list[BenchmarkCase]) -> BenchmarkReport:
    latencies=[]; rows=[]
    p_sum=r_sum=mrr_sum=ndcg_sum=0.0
    for case in cases:
        start=time.perf_counter()
        hits=engine.index.search(case.query, limit=case.k, mode=case.mode)
        latency=(time.perf_counter()-start)*1000
        latencies.append(latency)
        ids=[h.doc_id for h in hits]
        relevant=set(case.relevant)
        retrieved=set(ids)
        p=len(retrieved & relevant)/max(case.k,1)
        r=len(retrieved & relevant)/max(len(relevant),1)
        rr=next((1/i for i,d in enumerate(ids,1) if d in relevant),0.0)
        ideal=min(len(relevant),case.k)
        ideal_dcg=sum(1/math.log2(i+1) for i in range(1,ideal+1))
        ndcg=_dcg(ids,relevant,case.k)/ideal_dcg if ideal_dcg else 0.0
        p_sum+=p; r_sum+=r; mrr_sum+=rr; ndcg_sum+=ndcg
        rows.append({'query':case.query,'precision_at_k':round(p,5),'recall_at_k':round(r,5),'rr':round(rr,5),'ndcg_at_k':round(ndcg,5),'latency_ms':round(latency,3),'results':ids})
    s=sorted(latencies); p95=s[max(0,math.ceil(.95*len(s))-1)] if s else 0.0
    n=max(len(cases),1)
    return BenchmarkReport(len(cases),round(p_sum/n,5),round(r_sum/n,5),round(mrr_sum/n,5),round(ndcg_sum/n,5),round(sum(latencies)/n,3),round(p95,3),round(max(latencies,default=0),3),rows)


def save_report(report: BenchmarkReport, path: str | Path):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(asdict(report),indent=2),encoding='utf-8')
