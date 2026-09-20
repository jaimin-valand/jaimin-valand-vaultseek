# VaultSeek v3.0.0

A from-scratch, local-first private distributed search engine covering crawling, BM25 retrieval, hybrid search, durable indexing, sharding, replication, quorum consistency, educational Raft-style consensus, fault injection, snapshots, tracing, API security and operational tooling.

## Highlights

- Robots-aware concurrent crawling with incremental HTTP metadata.
- Positional inverted indexing, BM25, phrase queries and field-aware ranking.
- Hybrid lexical/local-semantic retrieval baseline.
- Compressed postings, WAL recovery, immutable segments and compaction.
- Deterministic sharding and parallel query fan-out.
- Remote shard RPC with retries, backoff, circuit breaking and partial results.
- Replication, quorum reads/writes, stale replica detection and read repair.
- Educational Raft-style consensus with persistence, network faults, snapshots and log compaction.
- Distributed tracing, latency telemetry and benchmark/evaluation tooling.
- FastAPI service with API-key authentication, rate limiting, request limits, readiness and graceful draining.
- Docker and GitHub Actions ready.

## Verification

- 55 tests passed.
- Python compilation passed.
- Release gate passed.
- Local API smoke/load test: 20/20 successful requests on the development machine.

## Important boundary

The consensus implementation is an educational Raft-style model, not production-grade consensus. Load-test numbers are environment-specific and are not production SLOs.

## Documentation

- [Architecture](docs/architecture.md)
- [v3.0 architecture diagram](docs/architecture-v3.0.svg)
- [v3.0 release notes](docs/v3.0.md)
- [Demo runbook](docs/demo.md)
- [Benchmarking](docs/benchmarking.md)
- [Crawling](docs/crawling.md)
- [Roadmap](docs/roadmap.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest -q
uvicorn private_search_engine.api.app:app --host 127.0.0.1 --port 8000
```

## License

MIT
