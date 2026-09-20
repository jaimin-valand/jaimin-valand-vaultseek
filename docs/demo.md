# 10-Minute Demo Runbook

This runbook is designed for a portfolio review, technical interview, or GitHub walkthrough.

## 1. Validate the release

```bash
python -m pytest -q
python -m compileall -q private_search_engine
python -m private_search_engine.cli release-gate
```

Expected result: all tests pass and the release gate prints `RELEASE_GATE_PASS`.

## 2. Start the API

```bash
uvicorn private_search_engine.api.app:app --host 127.0.0.1 --port 8765
```

Then open `/health`, `/ready`, and `/version`.

## 3. Explain retrieval

Show a search request and explain the pipeline:

```text
HTTP request
  -> validation/auth/rate limit
  -> query parsing
  -> lexical + phrase/hybrid retrieval
  -> shard fan-out
  -> ranking
  -> global top-K merge
  -> snippets + tracing
```

## 4. Explain reliability

Walk through WAL recovery, immutable segments, replication, quorum reads/writes, read repair, consensus, snapshots and fault injection.

## 5. Explain operations

Show request IDs, processing-time headers, health/readiness, rate limiting and the release gate.

## 6. Run the load test

Use the CLI load-test command against the local API. Report average/P95/max latency and request success rate, while clearly stating that these are local development-machine measurements.

## Interview talking points

- Why BM25 rather than a black-box hosted search service?
- Why immutable segments and WAL?
- Why shard before adding remote RPC?
- What does quorum consistency protect against?
- What is intentionally *not* production-grade?
- How would you evolve process-local rate limiting for a multi-instance deployment?
- How would you replace the deterministic semantic baseline with a private embedding model?
