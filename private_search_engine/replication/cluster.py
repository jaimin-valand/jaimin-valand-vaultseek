from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
import json, time
from threading import RLock
from ..core.document import Document

@dataclass
class ReplicaState:
    node_id: str
    role: str
    healthy: bool
    document_count: int
    generation: int
    checksum: str
    last_error: str | None = None
    last_sync_ms: float = 0.0
    def to_dict(self): return asdict(self)

class ReplicatedShard:
    """Deterministic primary/replica shard with checksum-based consistency checks."""
    def __init__(self, shard_id: int, root='data/replicas'):
        self.shard_id=shard_id; self.root=Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self._lock=RLock(); self.primary={}; self.replicas={}; self.generation=0; self.failed=set()

    def _checksum(self, docs):
        raw=json.dumps([d.to_dict() for d in sorted(docs.values(), key=lambda x:x.doc_id)], separators=(',', ':'), sort_keys=True).encode()
        return sha256(raw).hexdigest()

    def add_replica(self, node_id):
        if node_id in self.replicas: return
        self.replicas[node_id] = {}
        self.replicate(node_id)

    def add(self, doc: Document):
        with self._lock:
            self.primary[doc.doc_id]=doc; self.generation += 1
            for node in list(self.replicas):
                if node not in self.failed: self.replicate(node)

    def replicate(self, node_id):
        if node_id not in self.replicas: raise KeyError(node_id)
        started=time.perf_counter()
        if node_id in self.failed: raise RuntimeError(f'replica {node_id} unavailable')
        self.replicas[node_id] = dict(self.primary)
        return round((time.perf_counter()-started)*1000,4)

    def fail_replica(self,node_id): self.failed.add(node_id)
    def recover_replica(self,node_id): self.failed.discard(node_id); self.replicate(node_id)

    def state(self,node_id=None):
        docs=self.primary if node_id is None else self.replicas.get(node_id,{})
        return ReplicaState(node_id or f'primary-{self.shard_id}', 'primary' if node_id is None else 'replica', node_id not in self.failed if node_id else True, len(docs), self.generation, self._checksum(docs), None)

    def consistency(self):
        primary=self.state().checksum
        rows=[]
        for node in self.replicas:
            s=self.state(node); rows.append({'node_id':node,'consistent':s.checksum==primary and s.generation==self.generation,'primary_checksum':primary,'replica_checksum':s.checksum,'generation':s.generation,'primary_generation':self.generation})
        return rows

    def failover(self,node_id):
        if node_id not in self.replicas or node_id in self.failed: raise RuntimeError('replica unavailable')
        self.primary=dict(self.replicas[node_id]); self.generation=max(self.generation, self.state(node_id).generation)
        return self.state().to_dict()

class ClusterRebalancer:
    """Moves documents between shards using deterministic hash ownership."""
    def __init__(self, shard_count=4): self.shard_count=shard_count
    def owner(self, doc_id): return int.from_bytes(sha256(doc_id.encode()).digest()[:8],'big') % self.shard_count
    def plan(self, docs, current_shard):
        moves=[]
        for doc in docs:
            target=self.owner(doc.doc_id)
            if target != current_shard: moves.append({'doc_id':doc.doc_id,'from_shard':current_shard,'to_shard':target})
        return moves
