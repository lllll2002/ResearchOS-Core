"""
memory_search.py — Lightweight memory file search (BM25-like keyword ranking)
==============================================================================

Searches all .md memory files across vault-level and project-level memory directories.
No external dependencies — pure Python with TF-IDF-like scoring.

Usage:
    python memory_search.py "organoid sampling rate"
    python memory_search.py "shear-lag" --top 5
    python memory_search.py "deadline" --verbose
"""

import argparse
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

VAULT = Path(r"E:\Obsidian")

# All memory directories
MEMORY_DIRS = [
    VAULT / "memory",
    VAULT / "02_Research_Projects" / "Phase_Separation" / "memory",
    VAULT / "02_Research_Projects" / "Organoid_MEA_Chip" / "memory",
    VAULT / "02_Research_Projects" / "Biocomputing_Review" / "memory",
    VAULT / "02_Research_Projects" / "Apoptosis_Tissue_Simulation" / "memory",
    VAULT / "03_Theoretical_Work" / "Formula_Derivation" / "memory",
    VAULT / "03_Theoretical_Work" / "Literature_Review" / "memory",
]


def tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer, lowercased."""
    return re.findall(r"[a-z0-9\u4e00-\u9fff]+", text.lower())


def load_documents() -> list[dict]:
    """Load all .md files from memory directories."""
    docs = []
    for mem_dir in MEMORY_DIRS:
        if not mem_dir.exists():
            continue
        for md_file in mem_dir.rglob("*.md"):
            # Skip archive directories
            if "archive" in str(md_file).lower():
                continue
            try:
                content = md_file.read_text(encoding="utf-8")
                rel_path = md_file.relative_to(VAULT)
                docs.append({
                    "path": str(rel_path),
                    "name": md_file.stem,
                    "content": content,
                    "tokens": tokenize(content),
                    "size": len(content),
                })
            except Exception:
                continue
    return docs


def bm25_score(query_tokens: list[str], doc_tokens: list[str],
               doc_freq: dict[str, int], n_docs: int,
               avg_dl: float, k1: float = 1.5, b: float = 0.75) -> float:
    """Compute BM25 score for a single document."""
    tf = Counter(doc_tokens)
    dl = len(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        if qt not in tf:
            continue
        df = doc_freq.get(qt, 0)
        idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
        numerator = tf[qt] * (k1 + 1)
        denominator = tf[qt] + k1 * (1 - b + b * dl / avg_dl)
        score += idf * numerator / denominator
    return score


def search(query: str, top_k: int = 10, verbose: bool = False) -> list[dict]:
    """Search memory files with BM25 ranking."""
    docs = load_documents()
    if not docs:
        print("No memory files found.")
        return []

    query_tokens = tokenize(query)
    if not query_tokens:
        print("Empty query after tokenization.")
        return []

    # Compute document frequencies
    doc_freq: dict[str, int] = Counter()
    for doc in docs:
        unique_tokens = set(doc["tokens"])
        for t in unique_tokens:
            doc_freq[t] += 1

    n_docs = len(docs)
    avg_dl = sum(len(d["tokens"]) for d in docs) / n_docs

    # Score each document
    results = []
    for doc in docs:
        score = bm25_score(query_tokens, doc["tokens"], doc_freq, n_docs, avg_dl)
        if score > 0:
            results.append({**doc, "score": score})

    results.sort(key=lambda x: -x["score"])
    return results[:top_k]


def main():
    # Fix Windows GBK terminal encoding
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Search memory files")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--top", type=int, default=10, help="Number of results")
    parser.add_argument("--verbose", action="store_true", help="Show content snippets")
    args = parser.parse_args()

    results = search(args.query, top_k=args.top, verbose=args.verbose)

    if not results:
        print(f"No results for: {args.query}")
        return

    print(f"\nMemory search: \"{args.query}\" ({len(results)} results)\n")
    print(f"{'#':>2}  {'Score':>6}  {'File':<50}  {'Size':>6}")
    print("-" * 75)

    for i, r in enumerate(results, 1):
        print(f"{i:2d}  {r['score']:6.2f}  {r['path']:<50}  {r['size']:>5}B")
        if args.verbose:
            # Show first matching line
            query_tokens = set(tokenize(args.query))
            for line in r["content"].split("\n"):
                line_tokens = set(tokenize(line))
                if query_tokens & line_tokens:
                    snippet = line.strip()[:100]
                    print(f"      → {snippet}")
                    break
            print()


if __name__ == "__main__":
    main()
