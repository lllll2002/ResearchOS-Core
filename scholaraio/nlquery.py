"""
nlquery.py — 自然语言元数据查询（Text-to-SQL）
================================================

将自然语言问题转换为 SQL 查询，在论文元数据上执行。

用法：
    from scholaraio.nlquery import nl_search
    results = nl_search("2023年后引用量超过50的相分离论文", db_path, cfg=cfg)
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scholaraio.config import Config

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent routing
# ---------------------------------------------------------------------------

_INTENT_SYSTEM = """\
You are an intent classifier for an academic paper knowledge base.
Given a user question, classify it into exactly ONE of these intents:

1. "search" — The user wants to find papers by topic/keyword/author (e.g., "找相分离的论文", "organoid intelligence papers", "搜一下MEA相关的")
2. "data" — The user wants to query metadata with filters like year, citation count, journal, counts, aggregates (e.g., "2023年后引用量>50的论文", "有多少篇论文", "每年发表了多少篇")
3. "graph" — The user asks about entity relationships, claims, experiments, evidence chains (e.g., "哪些实验支持C-003", "G3BP1相关的所有实验", "C-001和C-003有什么关系")

Output ONLY a JSON object: {"intent": "search"|"data"|"graph", "reason": "<brief reason>"}
"""


def classify_intent(question: str, cfg: "Config") -> str:
    """Classify user question into search/data/graph intent."""
    from scholaraio.metrics import call_llm

    result = call_llm(
        question, cfg,
        system=_INTENT_SYSTEM,
        json_mode=True,
        max_tokens=100,
        purpose="intent",
    )
    try:
        resp = json.loads(result.content)
        intent = resp.get("intent", "search")
        if intent not in ("search", "data", "graph"):
            intent = "search"
        _log.info("Intent: %s (reason: %s)", intent, resp.get("reason", ""))
        return intent
    except (json.JSONDecodeError, KeyError):
        return "search"


_SCHEMA_DESCRIPTION = """\
Table: papers (FTS5 virtual table)
Columns:
  paper_id       TEXT  -- UUID, UNINDEXED
  title          TEXT  -- paper title, searchable
  authors        TEXT  -- author names, searchable
  year           TEXT  -- publication year (stored as text in FTS5)
  journal        TEXT  -- journal name
  abstract       TEXT  -- paper abstract, searchable
  conclusion     TEXT  -- conclusion paragraph, searchable
  doi            TEXT  -- UNINDEXED
  paper_type     TEXT  -- "journal-article", "review", "thesis", "posted-content", UNINDEXED
  citation_count TEXT  -- integer stored as text, UNINDEXED
  md_path        TEXT  -- UNINDEXED

Note: FTS5 columns marked UNINDEXED cannot be used in MATCH queries.
For text search use: WHERE papers MATCH '<keywords>'
For numeric filters use: CAST(year AS INTEGER), CAST(citation_count AS INTEGER)
For journal/paper_type use: journal LIKE '%pattern%'
Always SELECT paper_id, title, authors, year, journal, doi, citation_count.
ORDER BY and LIMIT are allowed. Maximum LIMIT 50.
"""

_FEW_SHOT = [
    {
        "q": "2023年后引用量超过50的相分离论文",
        "sql": "SELECT paper_id, title, authors, year, journal, doi, citation_count FROM papers WHERE papers MATCH 'phase separation' AND CAST(year AS INTEGER) >= 2023 AND CAST(citation_count AS INTEGER) > 50 ORDER BY CAST(citation_count AS INTEGER) DESC LIMIT 20",
    },
    {
        "q": "Nature上发表的综述文章",
        "sql": "SELECT paper_id, title, authors, year, journal, doi, citation_count FROM papers WHERE journal LIKE '%Nature%' AND paper_type LIKE '%review%' ORDER BY CAST(year AS INTEGER) DESC LIMIT 20",
    },
    {
        "q": "Zhang发表的关于organoid的文章，按年份排序",
        "sql": "SELECT paper_id, title, authors, year, journal, doi, citation_count FROM papers WHERE papers MATCH 'organoid' AND authors LIKE '%Zhang%' ORDER BY CAST(year AS INTEGER) DESC LIMIT 20",
    },
    {
        "q": "引用量最高的前10篇论文",
        "sql": "SELECT paper_id, title, authors, year, journal, doi, citation_count FROM papers ORDER BY CAST(citation_count AS INTEGER) DESC LIMIT 10",
    },
    {
        "q": "2020到2024年关于FPGA neural interface的文章",
        "sql": "SELECT paper_id, title, authors, year, journal, doi, citation_count FROM papers WHERE papers MATCH 'FPGA neural interface' AND CAST(year AS INTEGER) >= 2020 AND CAST(year AS INTEGER) <= 2024 ORDER BY CAST(citation_count AS INTEGER) DESC LIMIT 20",
    },
    {
        "q": "有多少篇论文",
        "sql": "SELECT COUNT(*) AS total FROM papers",
    },
    {
        "q": "每年发表了多少篇论文",
        "sql": "SELECT year, COUNT(*) AS count FROM papers GROUP BY year ORDER BY year DESC",
    },
]

_SYSTEM_PROMPT = f"""\
You are a Text-to-SQL assistant for an academic paper database.

{_SCHEMA_DESCRIPTION}

Rules:
1. Output ONLY a JSON object: {{"sql": "<SQL query>", "explanation": "<brief explanation in English>"}}
2. Use only SELECT statements. Never INSERT, UPDATE, DELETE, DROP, or ALTER.
3. For keyword search, use FTS5 MATCH syntax: WHERE papers MATCH '<terms>'
4. For numeric comparisons on year or citation_count, use CAST(... AS INTEGER)
5. Default LIMIT is 20 unless the user specifies otherwise. Max LIMIT 50.
6. Always include paper_id, title, authors, year, journal, doi, citation_count in SELECT for paper queries.
7. For aggregate queries (COUNT, GROUP BY), adapt columns as needed.
8. Keep the SQL simple and correct. Do not use subqueries unless necessary.
"""


def _build_prompt(question: str) -> str:
    examples = "\n".join(
        f'Q: {ex["q"]}\nSQL: {ex["sql"]}' for ex in _FEW_SHOT
    )
    return f"Examples:\n{examples}\n\nQ: {question}\nGenerate the SQL query."


def _validate_sql(sql: str) -> str | None:
    """Basic safety check. Returns error message or None if OK."""
    sql_upper = sql.upper().strip()
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "ATTACH"]
    for kw in forbidden:
        if re.search(rf"\b{kw}\b", sql_upper):
            return f"Forbidden keyword: {kw}"
    if not sql_upper.startswith("SELECT"):
        return "Query must start with SELECT"
    return None


_MAX_RETRIES = 2


def _generate_sql(question: str, cfg: "Config", repair_context: str = "") -> tuple[str, str]:
    """Call LLM to generate SQL. Returns (sql, explanation)."""
    from scholaraio.metrics import call_llm

    prompt = _build_prompt(question)
    if repair_context:
        prompt += f"\n\nPrevious attempt failed:\n{repair_context}\nFix the SQL."

    result = call_llm(
        prompt, cfg,
        system=_SYSTEM_PROMPT,
        json_mode=True,
        max_tokens=500,
        purpose="nlquery",
    )

    try:
        resp = json.loads(result.content)
        sql = resp["sql"].strip().rstrip(";")
        explanation = resp.get("explanation", "")
    except (json.JSONDecodeError, KeyError) as exc:
        raise RuntimeError(f"LLM 返回格式错误: {result.content}") from exc

    err = _validate_sql(sql)
    if err:
        raise RuntimeError(f"SQL 安全检查失败: {err}\nSQL: {sql}")

    return sql, explanation


def nl_search(
    question: str,
    db_path: Path,
    cfg: "Config | None" = None,
    top_k: int | None = None,
) -> dict:
    """Parse natural language question into SQL and execute.

    If the generated SQL fails, automatically feeds the error back to the
    LLM for self-repair (up to ``_MAX_RETRIES`` attempts).

    Args:
        question: Natural language query in any language.
        db_path: Path to the SQLite database.
        cfg: Config with LLM settings.
        top_k: Override result limit.

    Returns:
        Dict with keys: "sql", "explanation", "results", "columns",
        and "retries" (number of repair attempts used).

    Raises:
        RuntimeError: If LLM is not configured or all retries exhausted.
    """
    if cfg is None:
        from scholaraio.config import load_config
        cfg = load_config()

    sql, explanation = _generate_sql(question, cfg)
    last_error = ""
    retries = 0

    for attempt in range(_MAX_RETRIES + 1):
        # Override LIMIT if top_k specified
        final_sql = sql
        if top_k is not None:
            final_sql = re.sub(r"LIMIT\s+\d+", f"LIMIT {top_k}", final_sql)
            if "LIMIT" not in final_sql.upper():
                final_sql += f" LIMIT {top_k}"

        _log.info("nlquery SQL (attempt %d): %s", attempt + 1, final_sql)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(final_sql)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = [dict(row) for row in rows]
            conn.close()
            return {
                "sql": final_sql,
                "explanation": explanation,
                "columns": columns,
                "results": results,
                "retries": retries,
            }
        except sqlite3.OperationalError as exc:
            conn.close()
            last_error = str(exc)
            _log.warning("SQL failed (attempt %d): %s", attempt + 1, last_error)

            if attempt < _MAX_RETRIES:
                retries += 1
                repair_ctx = f"SQL: {final_sql}\nError: {last_error}"
                sql, explanation = _generate_sql(question, cfg, repair_context=repair_ctx)
            else:
                raise RuntimeError(
                    f"SQL 执行失败（已重试 {_MAX_RETRIES} 次）: {last_error}\nSQL: {final_sql}"
                ) from exc

    # Should not reach here
    raise RuntimeError("Unexpected state in nl_search")
