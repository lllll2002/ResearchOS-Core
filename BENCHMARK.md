# ScholarAIO Retrieval Benchmark

## Baseline

**Score**: 90% (9/10 propositions) — established 2026-04-25

**Command**: `scholaraio benchmark`

## Method

Reranker-based semantic proposition scoring:

1. Run 5 test queries via `usearch` (hybrid FTS5 + FAISS + reranker)
2. For each query, check 2 propositions against top-10 results
3. CrossEncoder (bge-reranker-v2-m3) scores each proposition vs result title+abstract
4. Proposition passes if best score >= 0.3
5. Overall score = passed propositions / total propositions

## Known Limitations

- Short propositions vs long documents can produce weak reranker signals (score 0.06 even when result is relevant)
- 90% is the reasonable ceiling for this method, not a sign of retrieval failure
- The 10% miss (B4) reflects the library's domain skew (MEA papers focus on organoid hardware, not generic electrophysiology), not a retrieval defect

## When to Investigate

- Score drops below **80%** → check if index.db is corrupted or embedding model changed
- Score drops below **70%** → rebuild vectors and chunks
- New query consistently fails → add it to BENCHMARK_QUERIES in `scholaraio/benchmark.py`

## History

Tracked in `data/benchmark_history.jsonl` (one JSON line per run).
Human-readable latest in `data/benchmark_latest.md` (auto-overwritten each run).
