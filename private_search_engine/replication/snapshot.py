from __future__ import annotations
import json
from hashlib import sha256
from pathlib import Path
from .consensus import LogEntry
class ConsensusSnapshotStore:
    """Atomic persistence for a compacted consensus state snapshot."""
    def __init__(self,path): self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
    @staticmethod
    def digest(state):
        body={k:v for k,v in state.items() if k!='checksum'}; return sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    def save(self,*,node_id,term,last_included_index,last_included_term,commit_index,state):
        payload={"node_id":node_id,"term":term,"last_included_index":last_included_index,"last_included_term":last_included_term,"commit_index":commit_index,"state":dict(sorted(state.items()))}; payload['checksum']=self.digest(payload); tmp=self.path.with_suffix(self.path.suffix+'.tmp'); tmp.write_text(json.dumps(payload,sort_keys=True,separators=(',',':')),encoding='utf-8'); tmp.replace(self.path); return payload['checksum']
    def load(self):
        if not self.path.exists(): return {"last_included_index":0,"last_included_term":0,"commit_index":0,"state":{}}
        payload=json.loads(self.path.read_text(encoding='utf-8')); checksum=payload.pop('checksum',None)
        if checksum!=self.digest(payload): raise ValueError('snapshot checksum mismatch')
        payload['checksum']=checksum; return payload

def compact_log(log,last_included_index): return [entry for entry in log if entry.index>last_included_index]
