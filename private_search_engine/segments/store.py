from __future__ import annotations
import json, os, time
from pathlib import Path
from ..core.document import Document
class SegmentStore:
    """Immutable JSON segment store with a small manifest and deterministic compaction."""
    def __init__(self,root='data/segments'):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True); self.manifest=self.root/'manifest.json'
        if not self.manifest.exists(): self._write_manifest([])
    def _read_manifest(self):
        try: return json.loads(self.manifest.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError): return []
    def _write_manifest(self,segments):
        tmp=self.manifest.with_suffix('.tmp'); tmp.write_text(json.dumps(segments,indent=2,sort_keys=True),encoding='utf-8'); os.replace(tmp,self.manifest)
    def list_segments(self): return self._read_manifest()
    def write_segment(self,documents):
        docs=sorted(documents,key=lambda d:d.doc_id); name=f'segment-{time.time_ns()}.json'; path=self.root/name; tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps([d.to_dict() for d in docs],separators=(',',':'),sort_keys=True),encoding='utf-8'); os.replace(tmp,path); segments=self._read_manifest(); segments.append(name); self._write_manifest(segments); return name
    def read_segment(self,name):
        path=self.root/name
        if not path.exists(): return []
        return [Document(x['url'],x['title'],x['text'],x.get('content_type','text/html')) for x in json.loads(path.read_text(encoding='utf-8'))]
    def all_documents(self):
        latest={}
        for name in self._read_manifest():
            for doc in self.read_segment(name): latest[doc.doc_id]=doc
        return sorted(latest.values(),key=lambda d:d.doc_id)
    def compact(self):
        segments=self._read_manifest()
        if len(segments)<=1: return False
        docs=self.all_documents(); compacted=f'segment-{time.time_ns()}-compacted.json'; path=self.root/compacted; tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps([d.to_dict() for d in docs],separators=(',',':'),sort_keys=True),encoding='utf-8'); os.replace(tmp,path); self._write_manifest([compacted])
        for name in segments:
            try: (self.root/name).unlink()
            except FileNotFoundError: pass
        return True
