from __future__ import annotations
import hashlib, math
from collections import Counter
from ..core.document import tokenize
class HashVectorizer:
    def __init__(self,dimensions=256): self.dimensions=dimensions
    def vector(self,text):
        v=[0.0]*self.dimensions; counts=Counter(tokenize(text))
        for term,tf in counts.items():
            digest=hashlib.blake2b(term.encode(),digest_size=8).digest(); idx=int.from_bytes(digest,'big')%self.dimensions; v[idx]+=1.0+math.log(tf)
        norm=math.sqrt(sum(x*x for x in v)) or 1.0; return [x/norm for x in v]
    @staticmethod
    def cosine(a,b): return sum(x*y for x,y in zip(a,b))
class HybridRanker:
    """Deterministic local semantic proxy; no external model or network required."""
    def __init__(self,alpha=.75): self.alpha=alpha; self.vectorizer=HashVectorizer()
    def rerank(self,query,hits,documents):
        q=self.vectorizer.vector(query); scored=[]
        for hit in hits:
            doc=documents[hit.doc_id]; semantic=self.vectorizer.cosine(q,self.vectorizer.vector(doc.title+' '+doc.text)); score=self.alpha*hit.score+(1-self.alpha)*semantic; scored.append((score,hit))
        scored.sort(key=lambda x:(-x[0],x[1].doc_id)); return [hit.__class__(hit.doc_id,round(score,5),hit.title,hit.url,hit.snippet) for score,hit in scored]
