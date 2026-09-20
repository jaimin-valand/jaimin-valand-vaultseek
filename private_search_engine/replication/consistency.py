from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from threading import RLock
from typing import Iterable

from ..core.document import Document


@dataclass(frozen=True)
class VersionedDocument:
    doc: Document
    version: int
    checksum: str

    @classmethod
    def create(cls, doc: Document, version: int) -> "VersionedDocument":
        return cls(doc, version, doc.content_hash)

    def to_dict(self):
        return {"doc": self.doc.to_dict(), "version": self.version, "checksum": self.checksum}


@dataclass(frozen=True)
class ConsistencyRead:
    doc_id: str
    version: int
    checksum: str
    replicas_observed: int
    quorum: int
    stale_replicas: int
    repaired: int
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class MutationResult:
    doc_id: str
    version: int
    acknowledgements: int
    required: int
    committed: bool
    def to_dict(self): return asdict(self)

class QuorumReplicaCluster:
    """Deterministic quorum/repair model for replicated search documents."""
    def __init__(self, node_ids: Iterable[str], read_quorum: int | None = None, write_quorum: int | None = None):
        self.nodes=list(dict.fromkeys(node_ids))
        if len(self.nodes)<1: raise ValueError("at least one node is required")
        n=len(self.nodes); self.read_quorum=read_quorum if read_quorum is not None else n//2+1; self.write_quorum=write_quorum if write_quorum is not None else n//2+1
        if not 1<=self.read_quorum<=n or not 1<=self.write_quorum<=n: raise ValueError("quorums must be between 1 and node count")
        if self.read_quorum+self.write_quorum<=n: raise ValueError("read_quorum + write_quorum must exceed node count")
        self._data={n:{} for n in self.nodes}; self._failed=set(); self._versions={}; self._lock=RLock()
    def _checksum(self,record): return sha256(f"{record.doc.doc_id}:{record.version}:{record.checksum}".encode()).hexdigest()
    def fail_node(self,node_id): self._require_node(node_id); self._failed.add(node_id)
    def recover_node(self,node_id): self._require_node(node_id); self._failed.discard(node_id)
    def _require_node(self,node_id):
        if node_id not in self._data: raise KeyError(node_id)
    def write(self,doc):
        with self._lock:
            version=self._versions.get(doc.doc_id,0)+1; record=VersionedDocument.create(doc,version); acknowledgements=0
            for node in self.nodes:
                if node in self._failed: continue
                self._data[node][doc.doc_id]=record; acknowledgements+=1
            if acknowledgements>=self.write_quorum: self._versions[doc.doc_id]=version
            return MutationResult(doc.doc_id,version,acknowledgements,self.write_quorum,acknowledgements>=self.write_quorum)
    def read(self,doc_id,repair=True):
        with self._lock:
            available=[n for n in self.nodes if n not in self._failed]
            if len(available)<self.read_quorum: raise RuntimeError("read quorum unavailable")
            observed=[]
            for node in available[:self.read_quorum]:
                record=self._data[node].get(doc_id)
                if record is not None: observed.append((node,record))
            if not observed: return None,ConsistencyRead(doc_id,0,"",len(available[:self.read_quorum]),self.read_quorum,0,0)
            winner=max(observed,key=lambda item:(item[1].version,item[1].checksum)); winner_record=winner[1]
            stale=[node for node,record in observed if record.version!=winner_record.version or record.checksum!=winner_record.checksum]; repaired=0
            if repair:
                for node in stale: self._data[node][doc_id]=winner_record; repaired+=1
                for node in available[self.read_quorum:]:
                    current=self._data[node].get(doc_id)
                    if current is None or current.version<winner_record.version: self._data[node][doc_id]=winner_record; repaired+=1
            return winner_record,ConsistencyRead(doc_id,winner_record.version,self._checksum(winner_record),len(observed),self.read_quorum,len(stale),repaired)
    def consistency(self,doc_id):
        rows=[]; records=[]
        for node in self.nodes:
            record=self._data[node].get(doc_id); records.append(record); rows.append({"node_id":node,"available":node not in self._failed,"version":record.version if record else 0,"checksum":record.checksum if record else None})
        target=max([r.version for r in records if r],default=0)
        for row in rows: row["consistent"]=row["version"]==target and target!=0
        return rows
    def stale_nodes(self,doc_id):
        rows=self.consistency(doc_id); target=max((x["version"] for x in rows),default=0); return [r["node_id"] for r in rows if r["version"]!=target]
    def stats(self): return {"nodes":len(self.nodes),"healthy_nodes":len([n for n in self.nodes if n not in self._failed]),"failed_nodes":sorted(self._failed),"read_quorum":self.read_quorum,"write_quorum":self.write_quorum}
