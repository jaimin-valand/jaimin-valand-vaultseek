from __future__ import annotations
import json, os
from pathlib import Path

class WriteAheadLog:
    """Durable append-only WAL. Recovery ignores malformed/truncated tail records."""
    def __init__(self, path='data/index.wal'):
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
    def append(self, operation: str, payload: dict) -> None:
        record=json.dumps({'operation':operation,'payload':payload},separators=(',',':'),sort_keys=True)
        with self.path.open('a',encoding='utf-8') as f:
            f.write(record+'\n'); f.flush(); os.fsync(f.fileno())
    def records(self):
        if not self.path.exists(): return []
        result=[]
        with self.path.open('r',encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                try: result.append(json.loads(line))
                except json.JSONDecodeError: break
        return result
    def checkpoint(self):
        tmp=self.path.with_suffix('.wal.tmp'); tmp.write_text('',encoding='utf-8'); os.replace(tmp,self.path)
