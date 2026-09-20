# Changelog

## 3.0.0 - Production-platform engineering milestone

### Added

- Environment-driven service configuration.
- Optional API-key authentication.
- Process-local sliding-window rate limiting.
- Request body-size protection.
- Request IDs and processing-time response headers.
- Readiness/draining lifecycle state.
- Concurrent HTTP load-test utility with average/P95/max latency reporting.
- Automated release gate combining tests and bytecode compilation.
- Container hardening with a non-root runtime user and health check.
- Security, contribution, demo and release documentation.

### Retained

- Same-host crawling with robots.txt and crawl-delay support.
- BM25, phrase, field-aware and hybrid retrieval.
- Compressed postings and immutable index segments.
- WAL recovery and compaction.
- Deterministic sharding and parallel fan-out.
- Remote shard RPC with retries and circuit breaking.
- Replication, quorum reads/writes and read repair.
- Educational Raft-style consensus, persistence, faults and snapshots.
- Distributed tracing and benchmark/evaluation tooling.

### Explicit limitations

The consensus implementation is an educational Raft-style model, not a production consensus implementation. Load-test measurements are machine- and workload-specific and must not be treated as production SLOs.

### Release hygiene

- Added an explicit MIT license and package metadata/links.
- Added a complete repository `.gitignore` covering runtime state, Python caches, environments and build artefacts.
- Removed local SQLite runtime state from the distributable source tree.
- Refreshed the README as the canonical v3.0.0 project landing page.
