import json
from pathlib import Path
from ..core.document import Document
class JsonStore:
    def __init__(self,path='data/index.json'): self.path=Path(path)
    def save(self,documents): self.path.parent.mkdir(parents=True,exist_ok=True); self.path.write_text(json.dumps([d.to_dict() for d in documents],indent=2),encoding='utf-8')
    def load(self):
        if not self.path.exists():return []
        return [Document(x['url'],x['title'],x['text'],x.get('content_type','text/html')) for x in json.loads(self.path.read_text(encoding='utf-8'))]
