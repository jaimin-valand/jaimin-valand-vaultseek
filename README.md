# VaultSeek

### Private Distributed Search Engine - v3.0.0

[![CI](https://github.com/jaimin-valand/jaimin-valand-vaultseek/actions/workflows/ci.yml/badge.svg)](https://github.com/jaimin-valand/jaimin-valand-vaultseek/actions/workflows/ci.yml)
[![Release](https://img.shields.io/badge/release-v3.0.0-blue)](https://github.com/jaimin-valand/jaimin-valand-vaultseek/releases/tag/v3.0.0)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

VaultSeek is a from-scratch, local-first search platform designed to demonstrate how a search engine evolves from crawling and information retrieval into a distributed systems platform.

It combines **BM25 retrieval, phrase search, incremental crawling, durable indexing, compressed postings, WAL recovery, immutable segments, sharding, remote RPC, replication, quorum consistency, Raft-style consensus, fault injection, snapshots, distributed tracing and service hardening** in one inspectable Python codebase.

> **Project boundary:** the consensus implementation is an educational Raft-style model, not a production consensus implementation. Performance numbers from local load tests are development-environment measurements, not production SLOs.

## Architecture

```text
Crawler
  -> Parser + Metadata
  -> Inverted / Positional Index
  -> BM25 + Phrase + Field-aware Retrieval
  -> Segments + WAL + Compression
  -> Deterministic Sharding
  -> Remote Fan-out + Global Top-K
  -> Replication + Quorum + Read Repair
  -> Raft-style Consensus + Snapshots
  -> FastAPI + Security + Observability
```

## Feature map

| Area | Capabilities |
|---|---|
| Crawling | Same-host frontier, robots.txt, crawl delay, retries, conditional HTTP metadata |
| Retrieval | BM25, AND/OR, phrase queries, positional indexing, title weighting, snippets |
| Evaluation | Precision@K, Recall@K, MRR, NDCG, average/P95/max latency |
| Storage | SQLite metadata, WAL, immutable segments, compaction, crash recovery |
| Distribution | Deterministic sharding, parallel fan-out, global top-K, remote shard RPC |
| Consistency | Replication, quorum reads/writes, checksums, read repair, rebalancing |
| Consensus | Leader election, terms, majority replication/commit, catch-up |
| Resilience | Fault injection, partitions, healing, snapshots, log compaction |
| Observability | Trace IDs, spans, per-stage latency, P95 and error metrics |
| Service hardening | API keys, constant-time comparison, rate limiting, body limits, request IDs, readiness |
| Delivery | Dockerfile, GitHub Actions CI, release gate, security/contribution docs |

## Verification

```text
55 passed
compileall: PASS
release gate: PASS
```

A local API smoke/load run also completed with 20/20 successful requests. These measurements are machine-specific development validation, not production SLOs.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -e '.[test]'
pytest -q
uvicorn private_search_engine.api.app:app --host 127.0.0.1 --port 8000
```

Operational endpoints:

```text
GET /health
GET /ready
GET /version
GET /stats
GET /search?q=python
```

Release gate:

```bash
python -m private_search_engine.cli release-gate
```

Local load test:

```bash
python -m private_search_engine.cli load-test http://127.0.0.1:8000/search --requests 100 --concurrency 10 --query python
```

## Configuration

```text
PSE_HOST=0.0.0.0
PSE_PORT=8000
PSE_API_KEY=<optional-secret>
PSE_RATE_LIMIT_PER_MINUTE=120
PSE_MAX_BODY_BYTES=1048576
PSE_MAX_REMOTE_NODES=32
PSE_MAX_TRACE_LIMIT=1000
PSE_ENV=production
```

Authentication remains disabled when `PSE_API_KEY` is empty for local development. Production deployments should provide a secret through an environment/secret manager.

## Documentation

- [Architecture](docs/architecture.md)
- [v3.0 architecture diagram](docs/architecture-v3.0.svg)
- [v3.0 platform notes](docs/v3.0.md)
- [10-minute demo / interview runbook](docs/demo.md)
- [Benchmarking](docs/benchmarking.md)
- [Crawling](docs/crawling.md)
- [Release checklist](docs/release-checklist.md)
- [Roadmap](docs/roadmap.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

Historical milestones are documented in `docs/v2.0.md` through `docs/v2.9.md`.

## Repository structure

```text
vaultseek/
├── .github/                 # CI and issue templates
├── docs/                    # Architecture, milestones and release docs
├── examples/                # Small benchmark/sample datasets
├── private_search_engine/
│   ├── api/                 # FastAPI service
│   ├── benchmark/           # IR evaluation
│   ├── core/                # Crawler, documents, index, engine
│   ├── distributed/         # Sharding and remote RPC
│   ├── persistence/         # WAL
│   ├── replication/         # Replication, quorum, consensus, snapshots
│   ├── retrieval/           # Compression and hybrid retrieval
│   ├── segments/            # Immutable segment store
│   ├── storage/             # JSON and SQLite stores
│   └── tests/               # 55 automated tests
├── Dockerfile
├── LICENSE
├── pyproject.toml
└── README.md
```

## Security boundary

VaultSeek demonstrates practical service controls but is not security-certified. Rate limiting is process-local. Consensus is educational/in-process rather than production-grade Raft. Docker was not built in the development environment used to prepare this source release.

## License

MIT - Copyright (c) 2026 Jaimin Valand.
