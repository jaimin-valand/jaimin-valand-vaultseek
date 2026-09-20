from dataclasses import dataclass, asdict
from hashlib import sha256
import re

@dataclass(frozen=True)
class Document:
    url: str
    title: str
    text: str
    content_type: str = "text/html"

    @property
    def content_hash(self) -> str:
        return sha256((self.title + "\n" + self.text + "\n" + self.content_type).encode("utf-8")).hexdigest()

    @property
    def doc_id(self) -> str:
        return sha256(self.url.encode()).hexdigest()[:16]

    def to_dict(self):
        d = asdict(self); d["doc_id"] = self.doc_id; return d

def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", text.lower())
