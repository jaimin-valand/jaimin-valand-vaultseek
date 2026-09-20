from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from .consensus import LogEntry
class ConsensusPersistence:
    """Atomic JSON persistence for consensus term, vote and replicated log."""
    def __init__(self,path): self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
    def save(self,*,node_id,term,voted_for,log,commit_index):
        payload={"node_id":node_id,"term":term,"voted_for":voted_for,"commit_index":commit_index,"log":[asdict(e) for e in log]}; tmp=self.path.with_suffix(self.path.suffix+'.tmp'); tmp.write_text(json.dumps(payload,sort_keys=True,separators=(',',':')),encoding='utf-8'); tmp.replace(self.path)
    def load(self):
        if not self.path.exists(): return {"term":0,"voted_for":None,"commit_index":0,"log":[]}
        raw=json.loads(self.path.read_text(encoding='utf-8')); raw['log']=[LogEntry(**entry) for entry in raw.get('log',[])]; return raw
