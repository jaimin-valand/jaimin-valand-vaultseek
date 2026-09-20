from __future__ import annotations
from dataclasses import dataclass
from random import Random
from typing import Callable, TypeVar
T=TypeVar("T")
@dataclass
class FaultEvent:
    source: str
    target: str
    action: str
    count: int = 1
class NetworkFaultInjector:
    """Deterministic transport fault model for consensus testing."""
    def __init__(self, seed: int = 7): self.random=Random(seed); self._rules={}; self.events=[]
    def drop(self,source,target): self._rules[(source,target)]="drop"
    def delay(self,source,target): self._rules[(source,target)]="delay"
    def partition(self,group_a,group_b):
        for a in group_a:
            for b in group_b: self.drop(a,b); self.drop(b,a)
    def heal(self): self._rules.clear()
    def send(self,source,target,fn):
        action=self._rules.get((source,target))
        if action: self.events.append(FaultEvent(source,target,action)); return None
        self.events.append(FaultEvent(source,target,"deliver")); return fn()
