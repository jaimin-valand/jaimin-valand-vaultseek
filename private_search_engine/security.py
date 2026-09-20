from __future__ import annotations
import hmac, time
from collections import defaultdict, deque
from threading import Lock
class RateLimiter:
    def __init__(self,limit=120,window_seconds=60): self.limit,self.window=limit,window_seconds; self._events=defaultdict(deque); self._lock=Lock()
    def allow(self,key):
        now=time.monotonic()
        with self._lock:
            q=self._events[key]; cutoff=now-self.window
            while q and q[0]<=cutoff: q.popleft()
            if len(q)>=self.limit: return False
            q.append(now); return True
    def reset(self):
        with self._lock: self._events.clear()
def valid_api_key(provided,expected):
    if not expected: return True
    return bool(provided) and hmac.compare_digest(provided,expected)
