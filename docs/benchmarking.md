# Search Benchmarking

The v1.3 benchmark harness measures Precision@K, Recall@K, MRR, NDCG@K and query latency.

A benchmark case contains a query, a set of relevant document IDs, query mode, and K. The harness executes the query against the local index, records latency, calculates IR metrics, and persists a JSON report.

Run:

```bash
python -m private_search_engine.cli benchmark examples/benchmark_cases.json
```

The benchmark is deterministic at the ranking layer; latency is environmental and should be compared on the same machine when tracking regressions.
