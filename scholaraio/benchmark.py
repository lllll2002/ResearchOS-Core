"""
benchmark.py — Retrieval quality benchmark (reranker-scored)
=============================================================

Runs test queries, uses the CrossEncoder reranker to score whether
results semantically match the expected propositions. No manual
keyword maintenance needed.

Usage:
    scholaraio benchmark
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scholaraio.config import Config

_log = logging.getLogger(__name__)

# Each test: query + propositions that top-10 results should satisfy
# Reranker scores each proposition against each result's title+abstract
BENCHMARK_QUERIES = [
    {
        "id": "B1",
        "query": "electric field effect on stress granule formation",
        "propositions": [
            "stress granule assembly or disassembly mechanism",
            "electric field or electrical stimulation on cells",
        ],
        "description": "Core topic — EF-SG papers",
    },
    {
        "id": "B2",
        "query": "organoid intelligence reservoir computing",
        "propositions": [
            "brain organoid or neural organoid computation",
            "reservoir computing or neuromorphic computing",
        ],
        "description": "Cross-domain — organoid + computation",
    },
    {
        "id": "B3",
        "query": "liquid-liquid phase separation nucleation thermodynamics",
        "propositions": [
            "liquid-liquid phase separation or biomolecular condensate",
            "nucleation or thermodynamic phase transition",
        ],
        "description": "Theory — LLPS basics",
    },
    {
        "id": "B4",
        "query": "MEA microelectrode array neural recording",
        "propositions": [
            "microelectrode array or multi-electrode recording",
            "neural network or brain organoid electrophysiology",
        ],
        "description": "Hardware — MEA papers",
    },
    {
        "id": "B5",
        "query": "DNA computing logic gates molecular",
        "propositions": [
            "DNA-based computing or molecular logic",
            "logic gates or programmable circuits",
        ],
        "description": "Biocomputing — DNA circuits",
    },
]

SCORE_THRESHOLD = 0.3  # CrossEncoder score threshold for proposition match


def run_benchmark(
    db_path: Path,
    cfg: "Config",
    top_k: int = 10,
) -> dict:
    """Run benchmark with reranker-scored proposition matching.

    For each query, retrieves top-k papers, then uses the CrossEncoder
    to check if at least one result satisfies each proposition.
    """
    from scholaraio.index import unified_search
    from scholaraio.vectors import _load_reranker

    reranker = _load_reranker(cfg)
    results_list = []
    total_pass = 0
    total_props = 0

    for case in BENCHMARK_QUERIES:
        search_results = unified_search(
            case["query"], db_path, top_k=top_k, cfg=cfg
        )

        # Build document texts from results
        docs = []
        for r in search_results:
            title = r.get("title", "")
            abstract = r.get("abstract") or ""
            docs.append(f"{title}. {abstract}"[:1000])

        # Score each proposition against all docs
        prop_results = []
        for prop in case["propositions"]:
            pairs = [(prop, doc) for doc in docs]
            if not pairs:
                prop_results.append({"proposition": prop, "best_score": 0.0, "passed": False})
                continue

            scores = reranker.predict(pairs)
            best_score = float(max(scores))
            passed = best_score >= SCORE_THRESHOLD

            prop_results.append({
                "proposition": prop,
                "best_score": round(best_score, 3),
                "passed": passed,
            })

        passed_count = sum(1 for p in prop_results if p["passed"])
        total_count = len(prop_results)
        score = passed_count / total_count if total_count else 1.0

        total_pass += passed_count
        total_props += total_count

        results_list.append({
            "id": case["id"],
            "query": case["query"],
            "description": case["description"],
            "propositions": prop_results,
            "score": score,
            "top_3": [r.get("title", "?")[:60] for r in search_results[:3]],
        })

    overall = total_pass / total_props if total_props else 1.0

    return {
        "timestamp": datetime.now().isoformat(),
        "method": "reranker-proposition",
        "threshold": SCORE_THRESHOLD,
        "overall_score": overall,
        "total_pass": total_pass,
        "total_propositions": total_props,
        "queries": results_list,
    }


def save_benchmark(report: dict, output_dir: Path) -> Path:
    """Append benchmark result to history and save readable markdown."""
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "benchmark_history.jsonl"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")

    md_path = output_dir / "benchmark_latest.md"
    lines = [
        f"# Retrieval Benchmark — {report['timestamp'][:10]}",
        f"",
        f"**Method**: Reranker proposition scoring (threshold={report['threshold']})",
        f"**Overall: {report['overall_score']:.0%}** ({report['total_pass']}/{report['total_propositions']} propositions passed)",
        f"",
        "| ID | Query | Score | Details |",
        "|---|-------|-------|---------|",
    ]
    for q in report["queries"]:
        failed = [p["proposition"][:30] for p in q["propositions"] if not p["passed"]]
        detail = f"missed: {', '.join(failed)}" if failed else "all passed"
        lines.append(f"| {q['id']} | {q['query'][:40]} | {q['score']:.0%} | {detail} |")

    lines.extend(["", "## Proposition Scores", ""])
    for q in report["queries"]:
        lines.append(f"**{q['id']}**: {q['query']}")
        for p in q["propositions"]:
            status = "PASS" if p["passed"] else "FAIL"
            lines.append(f"  [{status}] {p['best_score']:.3f} — {p['proposition']}")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    _log.info("Benchmark saved: %.0f%% -> %s", report["overall_score"] * 100, log_path)
    return log_path
