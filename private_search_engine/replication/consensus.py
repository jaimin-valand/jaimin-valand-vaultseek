from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from threading import RLock
from typing import Iterable

@dataclass(frozen=True)
class LogEntry:
    term: int
    index: int
    command: str
    value: str
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class ConsensusStatus:
    leader_id: str | None
    term: int
    commit_index: int
    applied_index: int
    role_by_node: dict[str, str]
    log_length: int
    healthy_nodes: int
    def to_dict(self): return asdict(self)

class RaftCluster:
    """Deterministic in-process Raft-style consensus model for educational/testing use.

    Models leader election, terms, majority replication, commit/apply and follower catch-up.
    It intentionally does not claim production-grade network consensus semantics.
    """
    def __init__(self, node_ids: Iterable[str]):
        self.nodes=list(dict.fromkeys(node_ids))
        if len(self.nodes)<3: raise ValueError("at least three nodes are required")
        self._lock=RLock(); self.term=0; self.leader_id=None; self.commit_index=0; self.applied_index=0
        self.logs={n:[] for n in self.nodes}; self._failed=set(); self._roles={n:"follower" for n in self.nodes}

    @property
    def majority(self): return len(self.nodes)//2+1
    def _require(self,node):
        if node not in self.logs: raise KeyError(node)
    def fail_node(self,node): self._require(node); self._failed.add(node); self._roles[node]="down"; self.leader_id = None if node==self.leader_id else self.leader_id
    def recover_node(self,node): self._require(node); self._failed.discard(node); self._roles[node]="follower"
    def elect_leader(self,node):
        self._require(node)
        if node in self._failed: raise RuntimeError("cannot elect failed node")
        healthy=len(self.nodes)-len(self._failed)
        if healthy < self.majority: raise RuntimeError("election quorum unavailable")
        self.term+=1; self.leader_id=node
        for n in self.nodes: self._roles[n] = "down" if n in self._failed else ("leader" if n==node else "follower")
        return self.status()
    def _replicate(self, entry):
        ack=0
        for n in self.nodes:
            if n in self._failed: continue
            if len(self.logs[n]) < entry.index: self.logs[n].append(entry)
            else: self.logs[n][entry.index-1]=entry
            ack+=1
        return ack
    def append(self, command, value):
        if self.leader_id is None or self.leader_id in self._failed: raise RuntimeError("no healthy leader")
        index=len(self.logs[self.leader_id])+1
        entry=LogEntry(self.term,index,command,value)
        ack=self._replicate(entry)
        if ack < self.majority: raise RuntimeError("majority unavailable")
        self.commit_index=index; self.applied_index=index
        return {"committed":True,"index":index,"term":self.term,"acknowledgements":ack,"required":self.majority}
    def catch_up(self,node):
        self._require(node)
        if node in self._failed: raise RuntimeError("node unavailable")
        if self.leader_id is None: raise RuntimeError("no leader")
        self.logs[node]=list(self.logs[self.leader_id])
        return len(self.logs[node])
    def state_digest(self,node):
        self._require(node)
        raw="|".join(f"{e.term}:{e.index}:{e.command}:{e.value}" for e in self.logs[node]).encode()
        return sha256(raw).hexdigest()
    def status(self):
        return ConsensusStatus(self.leader_id,self.term,self.commit_index,self.applied_index,dict(self._roles),len(self.logs[self.leader_id]) if self.leader_id else 0,len(self.nodes)-len(self._failed))
