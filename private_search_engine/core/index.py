from collections import Counter, defaultdict
from dataclasses import dataclass
import math
import re
from .document import Document, tokenize


@dataclass
class SearchHit:
    doc_id: str
    score: float
    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class ParsedQuery:
    terms: list[str]
    phrases: list[list[str]]
    mode: str = "OR"


class QueryParser:
    _phrase_re = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')

    @classmethod
    def parse(cls, query: str, mode: str = "OR") -> ParsedQuery:
        mode = mode.upper()
        if mode not in {"OR", "AND"}:
            raise ValueError("mode must be AND or OR")
        phrases = [tokenize(p) for p in cls._phrase_re.findall(query)]
        remaining = cls._phrase_re.sub(" ", query)
        terms = tokenize(remaining)
        return ParsedQuery(terms=terms, phrases=[p for p in phrases if p], mode=mode)


class InvertedIndex:
    def __init__(self):
        self.documents = {}
        self.postings = defaultdict(dict)
        self.positions = defaultdict(dict)
        self.title_terms = {}
        self.body_terms = {}
        self.doc_lengths = {}

    def add(self, doc: Document):
        if doc.doc_id in self.documents:
            self.remove(doc.doc_id)
        title = tokenize(doc.title)
        body = tokenize(doc.text)
        combined = title + body
        self.documents[doc.doc_id] = doc
        self.title_terms[doc.doc_id] = Counter(title)
        self.body_terms[doc.doc_id] = Counter(body)
        self.doc_lengths[doc.doc_id] = len(combined)
        all_terms = Counter(combined)
        for term, freq in all_terms.items():
            self.postings[term][doc.doc_id] = freq
        for pos, term in enumerate(body):
            self.positions[term].setdefault(doc.doc_id, []).append(pos)

    def remove(self, doc_id):
        self.documents.pop(doc_id, None)
        self.title_terms.pop(doc_id, None)
        self.body_terms.pop(doc_id, None)
        self.doc_lengths.pop(doc_id, None)
        for posting in self.postings.values():
            posting.pop(doc_id, None)
        for posting in self.positions.values():
            posting.pop(doc_id, None)

    def _idf(self, term):
        n = len(self.documents)
        df = len(self.postings.get(term, {}))
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    @staticmethod
    def _sequence_occurs(tokens, phrase):
        if not phrase or len(tokens) < len(phrase):
            return False
        return any(tokens[i:i + len(phrase)] == phrase for i in range(len(tokens) - len(phrase) + 1))

    @staticmethod
    def _phrase_occurs(doc_id, phrase, positions):
        if not phrase:
            return False
        first = positions.get(phrase[0], {}).get(doc_id, [])
        if not first:
            return False
        position_sets = [set(positions[t].get(doc_id, [])) for t in phrase[1:]]
        return any(all((start + offset) in position_sets[offset - 1] for offset in range(1, len(phrase))) for start in first)

    def search(self, query: str, limit=10, domain=None, content_type=None, mode="OR"):
        parsed = QueryParser.parse(query, mode)
        if not parsed.terms and not parsed.phrases:
            return []

        avgdl = sum(self.doc_lengths.values()) / max(len(self.documents), 1)
        k1, b = 1.5, 0.75
        scores = defaultdict(float)
        matched_terms = defaultdict(set)
        matched_phrases = defaultdict(int)

        candidates = set(self.documents)
        if parsed.mode == "AND" and parsed.terms:
            for term in parsed.terms:
                candidates &= set(self.postings.get(term, {}))
        elif parsed.terms:
            candidates = set().union(*(set(self.postings.get(t, {})) for t in parsed.terms))
        if parsed.phrases:
            phrase_candidates = set(self.documents)
            for phrase in parsed.phrases:
                phrase_candidates &= set(self.postings.get(phrase[0], {}))
            candidates &= phrase_candidates

        for doc_id in candidates:
            doc = self.documents[doc_id]
            host = self._host(doc.url)
            if domain and not (host == domain.lower() or host.endswith("." + domain.lower())):
                continue
            if content_type and doc.content_type != content_type:
                continue

            dl = self.doc_lengths[doc_id]
            score = 0.0
            for term in parsed.terms:
                freq = self.postings.get(term, {}).get(doc_id, 0)
                if not freq:
                    continue
                norm = freq + k1 * (1 - b + b * dl / max(avgdl, 1))
                score += self._idf(term) * ((freq * (k1 + 1)) / norm)
                matched_terms[doc_id].add(term)
                if self.title_terms[doc_id].get(term):
                    score += self._idf(term) * 1.25 * self.title_terms[doc_id][term]

            for phrase in parsed.phrases:
                body_match = self._phrase_occurs(doc_id, phrase, self.positions)
                title_tokens = list(self.title_terms[doc_id].elements())
                title_match = self._sequence_occurs(title_tokens, phrase)
                if body_match or title_match:
                    matched_phrases[doc_id] += 1
                    score += 2.5 * sum(self._idf(t) for t in phrase) + 3.0
                    if title_match:
                        score += 5.0
                elif parsed.mode == "AND":
                    score = 0.0
                    break

            if parsed.mode == "AND" and len(matched_terms[doc_id]) < len(set(parsed.terms)):
                continue
            if score > 0:
                score += 0.5 * matched_phrases[doc_id]
                scores[doc_id] = score

        hits = []
        for doc_id, score in sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:limit]:
            doc = self.documents[doc_id]
            terms = parsed.terms + [t for p in parsed.phrases for t in p]
            hits.append(SearchHit(doc_id, round(score, 5), doc.title, doc.url, self._snippet(doc, terms)))
        return hits

    @staticmethod
    def _host(url):
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower().split(":", 1)[0]

    @staticmethod
    def _snippet(doc, terms):
        text = " ".join(doc.text.split())
        low = text.lower()
        positions = [low.find(t.lower()) for t in terms if low.find(t.lower()) >= 0]
        start = max(min(positions) - 80, 0) if positions else 0
        snippet = text[start:start + 220]
        return ("..." if start else "") + snippet + ("..." if start + 220 < len(text) else "")
