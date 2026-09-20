# Architecture

## Retrieval pipeline

1. `QueryParser` separates quoted phrases from ordinary terms and validates AND/OR mode.
2. `InvertedIndex` maintains document, posting, title-frequency, body-frequency and body-position structures.
3. Candidate selection applies Boolean semantics before scoring.
4. BM25 scores ordinary terms using document-length normalisation and inverse document frequency.
5. Title matches receive an additional field-weighted score.
6. Exact body phrases receive a phrase bonus using positional postings.
7. Results are rendered with snippets around the first matching term.

## Incremental crawl state

SQLite stores URL, ETag, Last-Modified and content hash metadata. The crawler sends conditional requests where validators are available and avoids replacing unchanged documents.

## Design principles

- Local-first storage
- Deterministic ranking
- Small dependency surface
- Explicit query semantics
- Search index separated from crawl metadata
- Safe, host-bounded crawling
