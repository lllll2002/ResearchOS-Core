"""
summarize.py — 递归分批文献综合（Map-Reduce 风格）
=====================================================

解决大量论文超出 LLM context window 的问题。
不一次塞入所有论文，而是分批处理：
  每批 N 篇 → 生成中间摘要 → 合并中间摘要 → 最终输出

灵感来源：RLM (Recursive Language Models, MIT CSAIL 2025)

用法：
    from scholaraio.summarize import recursive_summarize
    result = recursive_summarize(papers, query="相分离与电场的关系", cfg=cfg)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scholaraio.config import Config

_log = logging.getLogger(__name__)

_MAP_SYSTEM = """\
You are a research assistant summarizing academic papers.
Given a batch of papers (title + abstract), produce a concise synthesis paragraph that:
1. Identifies the key findings and methods across these papers
2. Notes agreements and disagreements between papers
3. Highlights gaps or open questions
4. Relates findings to the user's query

Output a single paragraph (200-300 words) in English.
Do NOT list papers one by one — synthesize across them.
"""

_REDUCE_SYSTEM = """\
You are a research assistant merging multiple intermediate summaries into a final synthesis.
Given several batch summaries (each covering a group of papers), produce a comprehensive synthesis that:
1. Integrates findings across all batches
2. Identifies overarching themes and consensus
3. Notes contradictions or debates in the field
4. Highlights the most significant gaps
5. Provides a clear narrative structure

Output a well-structured synthesis (400-600 words) in English.
"""


def _call_model(prompt: str, cfg: "Config", *, system: str, max_tokens: int,
                 purpose: str, use_local: bool = False, local_model: str = "qwen3:8b"):
    """Route LLM call to cloud API or local Ollama."""
    if use_local:
        return _call_ollama(prompt, system=system, model=local_model, max_tokens=max_tokens)
    from scholaraio.metrics import call_llm
    return call_llm(prompt, cfg, system=system, json_mode=False,
                    max_tokens=max_tokens, purpose=purpose)


def _call_ollama(prompt: str, *, system: str, model: str = "qwen3:8b",
                 max_tokens: int = 1000):
    """Call local Ollama model directly via HTTP."""
    import requests
    from dataclasses import dataclass

    @dataclass
    class OllamaResult:
        content: str

    # Use Ollama native API (more reliable than OpenAI-compat for large payloads)
    try:
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"/no_think {prompt}"},
                ],
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": max_tokens},
            },
            timeout=180,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return OllamaResult(content=content)
    except Exception as exc:
        _log.warning("Ollama call failed: %s", exc)
        raise


def recursive_summarize(
    papers: list[dict],
    query: str,
    cfg: "Config",
    *,
    batch_size: int = 8,
    max_abstract_chars: int = 500,
    use_local: bool = False,
    local_model: str = "qwen3:8b",
) -> dict:
    """Recursively summarize a large set of papers using map-reduce.

    Args:
        papers: List of paper dicts with at least "title" and "abstract" keys.
        query: User's research question (guides the synthesis focus).
        cfg: Config with LLM settings.
        batch_size: Papers per batch in the map phase.
        max_abstract_chars: Truncate abstracts to this length per paper.
        use_local: If True, use local Ollama model instead of cloud API.
        local_model: Ollama model name (default: qwen3:8b).

    Returns:
        Dict with "final_summary", "batch_summaries", "paper_count", "batch_count".
    """

    kw = dict(use_local=use_local, local_model=local_model)

    if not papers:
        return {"final_summary": "", "batch_summaries": [], "paper_count": 0, "batch_count": 0}

    # If small enough, just do a single pass
    if len(papers) <= batch_size:
        prompt = _format_batch(papers, query, max_abstract_chars)
        result = _call_model(prompt, cfg, system=_MAP_SYSTEM,
                             max_tokens=1000, purpose="summarize.single", **kw)
        return {
            "final_summary": result.content,
            "batch_summaries": [result.content],
            "paper_count": len(papers),
            "batch_count": 1,
        }

    # --- Map phase: process batches ---
    batch_summaries = []
    for i in range(0, len(papers), batch_size):
        batch = papers[i:i + batch_size]
        prompt = _format_batch(batch, query, max_abstract_chars)
        _log.info("Map batch %d/%d (%d papers)",
                  i // batch_size + 1,
                  (len(papers) + batch_size - 1) // batch_size,
                  len(batch))

        result = _call_model(prompt, cfg, system=_MAP_SYSTEM,
                             max_tokens=800, purpose="summarize.map", **kw)
        batch_summaries.append(result.content)

    # --- Reduce phase: merge batch summaries ---
    if len(batch_summaries) > batch_size:
        _log.info("Recursive reduce: %d summaries to merge", len(batch_summaries))
        pseudo_papers = [{"title": f"Batch {i+1} Summary", "abstract": s}
                         for i, s in enumerate(batch_summaries)]
        sub_result = recursive_summarize(pseudo_papers, query, cfg,
                                         batch_size=batch_size,
                                         max_abstract_chars=2000,
                                         use_local=use_local,
                                         local_model=local_model)
        return {
            "final_summary": sub_result["final_summary"],
            "batch_summaries": batch_summaries,
            "paper_count": len(papers),
            "batch_count": len(batch_summaries),
        }

    # Single reduce pass
    reduce_prompt = f"Query: {query}\n\n"
    for i, summary in enumerate(batch_summaries):
        reduce_prompt += f"--- Batch {i+1} Summary ---\n{summary}\n\n"
    reduce_prompt += "Merge these batch summaries into a comprehensive final synthesis."

    _log.info("Reduce: merging %d batch summaries", len(batch_summaries))
    result = _call_model(reduce_prompt, cfg, system=_REDUCE_SYSTEM,
                         max_tokens=2000, purpose="summarize.reduce", **kw)

    return {
        "final_summary": result.content,
        "batch_summaries": batch_summaries,
        "paper_count": len(papers),
        "batch_count": len(batch_summaries),
    }


def _format_batch(papers: list[dict], query: str, max_chars: int) -> str:
    """Format a batch of papers into a prompt."""
    lines = [f"Query: {query}\n"]
    for i, p in enumerate(papers, 1):
        title = p.get("title", "Unknown")
        abstract = (p.get("abstract") or "")[:max_chars]
        year = p.get("year", "")
        authors = p.get("authors", "")
        if isinstance(authors, list):
            authors = ", ".join(authors[:3])
        lines.append(f"[{i}] {title}")
        if year:
            lines.append(f"    Year: {year}")
        if authors:
            lines.append(f"    Authors: {authors}")
        if abstract:
            lines.append(f"    Abstract: {abstract}")
        lines.append("")
    lines.append("Synthesize these papers in relation to the query.")
    return "\n".join(lines)


def summarize_workspace(
    ws_name: str,
    query: str,
    cfg: "Config",
    *,
    batch_size: int = 8,
    use_local: bool = False,
    local_model: str = "qwen3:8b",
) -> dict:
    """Summarize all papers in a ScholarAIO workspace using recursive map-reduce.

    Args:
        ws_name: Workspace name (e.g., "biocomputing").
        query: Research question to focus the synthesis.
        cfg: Config with LLM and path settings.
        batch_size: Papers per batch.
        use_local: Use local Ollama model instead of cloud API.
        local_model: Ollama model name.

    Returns:
        Dict with summary results.
    """
    import sqlite3

    # Load workspace paper IDs
    ws_path = cfg.papers_dir.parent.parent / "workspace" / ws_name / "papers.json"
    if not ws_path.exists():
        raise FileNotFoundError(f"Workspace not found: {ws_name}")

    ws_papers = json.loads(ws_path.read_text(encoding="utf-8"))
    paper_ids = {p["id"] for p in ws_papers}

    # Load metadata for each paper
    papers = []
    conn = sqlite3.connect(cfg.index_db)
    try:
        for pid in paper_ids:
            row = conn.execute(
                "SELECT title, authors, year, abstract FROM papers WHERE paper_id = ?",
                (pid,)
            ).fetchone()
            if row:
                papers.append({
                    "title": row[0] or "",
                    "authors": row[1] or "",
                    "year": row[2] or "",
                    "abstract": row[3] or "",
                })
    finally:
        conn.close()

    _log.info("Summarizing workspace '%s': %d papers, query='%s'",
              ws_name, len(papers), query[:50])

    return recursive_summarize(papers, query, cfg, batch_size=batch_size,
                              use_local=use_local, local_model=local_model)
