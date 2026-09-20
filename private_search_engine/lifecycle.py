from __future__ import annotations
from dataclasses import dataclass
from threading import Lock
import time

@dataclass
class Lifecycle:
    ready: bool = True
    draining: bool = False
    started_at: float = time.time()
    _lock: Lock = Lock()
    def begin_shutdown(self):
        with self._lock:
            self.draining = True
            self.ready = False
    def status(self):
        return {'ready': self.ready, 'draining': self.draining, 'uptime_seconds': round(time.time()-self.started_at, 3)}
