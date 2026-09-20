from __future__ import annotations
from dataclasses import dataclass, field
from contextlib import contextmanager
from threading import RLock
from time import perf_counter
from uuid import uuid4
from collections import Counter
import json

@dataclass
class TraceEvent:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start_ms: float
    duration_ms: float
    status: str = "ok"
    attributes: dict = field(default_factory=dict)

    def to_dict(self):
        return {"trace_id": self.trace_id, "span_id": self.span_id, "parent_span_id": self.parent_span_id,
                "name": self.name, "start_ms": self.start_ms, "duration_ms": self.duration_ms,
                "status": self.status, "attributes": self.attributes}

class SearchTrace:
    def __init__(self, trace_id=None):
        self.trace_id = trace_id or uuid4().hex
        self.events=[]; self.started=perf_counter(); self._lock=RLock()
    @contextmanager
    def span(self, name, parent_span_id=None, **attributes):
        span_id=uuid4().hex[:16]; started=perf_counter(); status="ok"; error=None
        try: yield span_id
        except Exception as exc:
            status="error"; error=f"{type(exc).__name__}: {exc}"; raise
        finally:
            attrs=dict(attributes)
            if error: attrs["error"] = error
            event=TraceEvent(self.trace_id,span_id,parent_span_id,name,round((started-self.started)*1000,4),round((perf_counter()-started)*1000,4),status,attrs)
            with self._lock: self.events.append(event)
    def finish(self):
        with self._lock: return [e.to_dict() for e in self.events]
    def summary(self):
        events=self.finish(); durations=[e["duration_ms"] for e in events]
        by_name={}
        for e in events:
            by_name.setdefault(e["name"],[]).append(e["duration_ms"])
        return {"trace_id":self.trace_id,"spans":len(events),"duration_ms":round(sum(durations),4),
                "errors":sum(e["status"]=="error" for e in events),
                "stages":{k:{"count":len(v),"total_ms":round(sum(v),4),"max_ms":round(max(v),4)} for k,v in by_name.items()}}

class TraceStore:
    def __init__(self, max_traces=1000): self.max_traces=max_traces; self._traces=[]; self._lock=RLock()
    def add(self, trace):
        with self._lock:
            self._traces.append(trace); self._traces=self._traces[-self.max_traces:]
    def traces(self):
        with self._lock: return [t.summary() for t in reversed(self._traces)]
    def get(self, trace_id):
        with self._lock:
            for t in self._traces:
                if t.trace_id==trace_id: return {"summary":t.summary(),"events":t.finish()}
        return None
    def metrics(self):
        summaries=self.traces(); durations=[s["duration_ms"] for s in summaries]
        durations.sort()
        p95=durations[min(len(durations)-1,max(0,int(len(durations)*.95)-1))] if durations else 0.0
        stage=Counter()
        for s in summaries: stage.update({k:v["count"] for k,v in s["stages"].items()})
        return {"traces":len(summaries),"errors":sum(s["errors"] for s in summaries),
                "avg_latency_ms":round(sum(durations)/len(durations),4) if durations else 0.0,
                "p95_latency_ms":round(p95,4),"stage_counts":dict(stage)}
    def export(self, path):
        payload={"metrics":self.metrics(),"traces":[self.get(s["trace_id"]) for s in self.traces()]}
        path.write_text(json.dumps(payload,indent=2),encoding="utf-8"); return payload
