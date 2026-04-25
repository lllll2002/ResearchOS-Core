"""
vectors.py — 向量嵌入与语义检索
==================================

使用 Qwen3-Embedding-0.6B（本地 ModelScope 缓存）生成论文向量。
嵌入文本 = title + abstract，存入 index.db 的 paper_vectors 表。

用法：
    from scholaraio.vectors import build_vectors, vsearch
    build_vectors(papers_dir, db_path)
    results = vsearch("turbulent drag reduction", db_path, top_k=5)
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import sqlite3
import struct
from pathlib import Path
import logging
from typing import TYPE_CHECKING

_log = logging.getLogger(__name__)

if TYPE_CHECKING:
    import faiss

    from scholaraio.config import Config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_vectors (
    paper_id     TEXT PRIMARY KEY,
    embedding    BLOB NOT NULL,
    content_hash TEXT NOT NULL DEFAULT ''
);
"""

_MIGRATE_HASH = (
    "ALTER TABLE paper_vectors ADD COLUMN content_hash TEXT NOT NULL DEFAULT ''"
)


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create paper_vectors table and migrate schema if needed."""
    conn.execute(_SCHEMA)
    # Migrate: add content_hash column if missing
    cols = {row[1] for row in conn.execute("PRAGMA table_info(paper_vectors)")}
    if "content_hash" not in cols:
        conn.execute(_MIGRATE_HASH)


def _content_hash(title: str, abstract: str) -> str:
    """Compute a short hash of the embedding source text."""
    text = f"{title}\n\n{abstract}"
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


# ============================================================================
#  Embedding
# ============================================================================

_model_cache: dict = {}  # key: (model_path, device) → SentenceTransformer


def _load_model(cfg: Config | None = None):
    """Load SentenceTransformer, using module-level cache to avoid reloading."""
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    SentenceTransformer = importlib.import_module("sentence_transformers").SentenceTransformer

    # Resolve config
    if cfg is not None:
        model_name = cfg.embed.model
        cache_dir = os.path.expanduser(cfg.embed.cache_dir)
        device_cfg = cfg.embed.device
        source = cfg.embed.source
    else:
        model_name = "Qwen/Qwen3-Embedding-0.6B"
        cache_dir = os.path.expanduser("~/.cache/modelscope/hub/models")
        device_cfg = "auto"
        source = "modelscope"

    # Resolve device
    if device_cfg == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"
    else:
        device = device_cfg

    cache_key = (model_name, cache_dir, device)
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    # Try to find or download the model
    local_path = _resolve_model_path(model_name, cache_dir, source)
    if local_path:
        model = SentenceTransformer(local_path, device=device)
    else:
        # HuggingFace fallback: SentenceTransformer handles download internally
        _log.info("[embed] downloading model %s from HuggingFace", model_name)
        model = SentenceTransformer(model_name, device=device)

    _model_cache[cache_key] = model
    return model


def _resolve_model_path(model_name: str, cache_dir: str, source: str) -> str | None:
    """Find local model path or download via ModelScope.

    Args:
        model_name: Model ID (e.g. ``"Qwen/Qwen3-Embedding-0.6B"``).
        cache_dir: Local cache directory.
        source: ``"modelscope"`` or ``"huggingface"``.

    Returns:
        Local folder path if found or downloaded, ``None`` to fall back
        to HuggingFace (SentenceTransformer handles download internally).
    """
    if source != "modelscope":
        return None

    try:
        from modelscope import snapshot_download
    except ImportError:
        return None

    # Check if already cached locally
    try:
        local_path = snapshot_download(model_name, cache_dir=cache_dir, local_files_only=True)
        return local_path
    except Exception as e:
        _log.debug("model not cached locally: %s", e)

    # Download
    try:
        _log.info("[embed] downloading model %s from ModelScope", model_name)
        return snapshot_download(model_name, cache_dir=cache_dir)
    except Exception as e:
        _log.warning("[embed] ModelScope download failed: %s, falling back to HuggingFace", e)
    return None


def _embed_text(text: str, cfg: Config | None = None) -> list[float]:
    model = _load_model(cfg)
    vec = model.encode([text], prompt_name="query", normalize_embeddings=True)
    return vec[0].tolist()


def _embed_batch(texts: list[str], cfg: Config | None = None) -> list[list[float]]:
    model = _load_model(cfg)
    vecs = model.encode(texts, normalize_embeddings=True, batch_size=16)
    return vecs.tolist()


# ============================================================================
#  Reranker
# ============================================================================

_reranker_cache: dict = {}  # key: (model_path, device) → CrossEncoder


def _load_reranker(cfg: Config | None = None):
    """Load CrossEncoder reranker, using module-level cache."""
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    CrossEncoder = importlib.import_module("sentence_transformers").CrossEncoder

    if cfg is not None:
        model_name = cfg.reranker.model
        device_cfg = cfg.reranker.device
        source = cfg.reranker.source
    else:
        model_name = "BAAI/bge-reranker-v2-m3"
        device_cfg = "auto"
        source = "modelscope"

    if device_cfg == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"
    else:
        device = device_cfg

    cache_dir = os.path.expanduser(
        cfg.embed.cache_dir if cfg is not None else "~/.cache/modelscope/hub/models"
    )
    cache_key = (model_name, device)
    if cache_key in _reranker_cache:
        return _reranker_cache[cache_key]

    local_path = _resolve_model_path(model_name, cache_dir, source)
    if local_path:
        model = CrossEncoder(local_path, device=device)
    else:
        _log.info("[reranker] downloading model %s from HuggingFace", model_name)
        model = CrossEncoder(model_name, device=device)

    _reranker_cache[cache_key] = model
    return model


def rerank(
    query: str,
    candidates: list[dict],
    cfg: Config | None = None,
    top_k: int | None = None,
) -> list[dict]:
    """Rerank candidate papers using a CrossEncoder model.

    Each candidate dict must have a ``"title"`` key.  If ``"abstract"`` is
    present it is appended for richer context.

    Args:
        query: Original search query.
        candidates: List of paper dicts from the merge stage.
        cfg: Optional config.
        top_k: Maximum results to return after reranking.

    Returns:
        Reranked list, each dict augmented with ``"rerank_score"``.
    """
    if not candidates:
        return candidates

    # Build (query, document) pairs
    pairs: list[tuple[str, str]] = []
    for c in candidates:
        doc = c.get("title", "")
        abstract = c.get("abstract") or ""
        if abstract:
            doc = f"{doc}. {abstract}"
        pairs.append((query, doc))

    model = _load_reranker(cfg)
    scores = model.predict(pairs)

    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)

    reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
    if top_k:
        reranked = reranked[:top_k]
    return reranked


class QwenEmbedder:
    """BERTopic-compatible embedder wrapping Qwen3 via ``_embed_batch``.

    BERTopic's KeyBERTInspired representation model requires an embedding
    backend that exposes ``embed_documents`` and ``embed_words`` methods.
    This class provides that interface.

    Args:
        cfg: Optional Config (or None) forwarded to ``_embed_batch``.
    """

    def __init__(self, cfg: Config | None = None):
        self._cfg = cfg

    def embed_documents(self, documents, verbose=False):
        import numpy as np
        return np.array(_embed_batch(documents, self._cfg), dtype="float32")

    def embed_words(self, words, verbose=False):
        return self.embed_documents(words, verbose)


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def _faiss_paths(db_path: Path) -> tuple[Path, Path]:
    """Return (faiss_index_path, faiss_ids_path) next to the db file."""
    parent = db_path.parent
    return parent / "faiss.index", parent / "faiss_ids.json"


def _invalidate_faiss(db_path: Path) -> None:
    """Delete cached FAISS index files so next search rebuilds them."""
    for p in _faiss_paths(db_path):
        p.unlink(missing_ok=True)


def _append_faiss_files(
    index_path: Path,
    ids_path: Path,
    new_ids: list[str],
    new_vecs: list[list[float]],
) -> None:
    """Append new vectors to a FAISS index at explicit file paths.

    If the cached index does not exist yet, does nothing (it will be built on
    next search).  If any new IDs overlap with existing ones, the cached index
    is deleted so it gets rebuilt.

    Args:
        index_path: Path to ``faiss.index`` file.
        ids_path: Path to ``faiss_ids.json`` file.
        new_ids: New paper IDs.
        new_vecs: Corresponding embedding vectors (already normalised).
    """
    import faiss
    import numpy as np

    if not index_path.exists() or not ids_path.exists():
        return

    try:
        index = faiss.read_index(str(index_path))
        paper_ids = json.loads(ids_path.read_text("utf-8"))
    except Exception as e:
        _log.debug("failed to load FAISS cache, rebuilding: %s", e)
        index_path.unlink(missing_ok=True)
        ids_path.unlink(missing_ok=True)
        return

    if set(new_ids) & set(paper_ids):
        index_path.unlink(missing_ok=True)
        ids_path.unlink(missing_ok=True)
        return

    arr = np.array(new_vecs, dtype="float32")
    faiss.normalize_L2(arr)
    index.add(arr)
    paper_ids.extend(new_ids)

    faiss.write_index(index, str(index_path))
    ids_path.write_text(
        json.dumps(paper_ids, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _append_faiss(db_path: Path, new_ids: list[str], new_vecs: list[list[float]]) -> None:
    """Append new vectors to existing FAISS index, or invalidate if not possible.

    Args:
        db_path: SQLite 数据库路径。
        new_ids: 新增论文 ID 列表。
        new_vecs: 对应的向量列表（已归一化）。
    """
    idx_p, ids_p = _faiss_paths(db_path)
    _append_faiss_files(idx_p, ids_p, new_ids, new_vecs)


# ============================================================================
#  Build
# ============================================================================


def build_vectors(papers_dir: Path, db_path: Path, rebuild: bool = False, cfg: Config | None = None) -> int:
    """为论文生成语义嵌入向量并写入 ``paper_vectors`` 表。

    嵌入文本 = ``title`` + ``abstract`` 拼接。
    使用 Sentence Transformer 模型（默认 Qwen3-Embedding-0.6B）。

    Args:
        papers_dir: 已入库论文目录，扫描其中的 ``*.json``。
        db_path: SQLite 数据库路径，不存在时自动创建。
        rebuild: 为 ``True`` 时清空旧向量后重建。
        cfg: 可选的 :class:`~scholaraio.config.Config`，用于读取模型/设备配置。

    Returns:
        本次新写入的向量数量。
    """
    conn = sqlite3.connect(db_path)
    try:
        _ensure_schema(conn)

        if rebuild:
            conn.execute("DELETE FROM paper_vectors")

        # Build lookup of existing hashes for incremental check
        existing_hashes: dict[str, str] = {}
        if not rebuild:
            for row in conn.execute(
                "SELECT paper_id, content_hash FROM paper_vectors"
            ).fetchall():
                existing_hashes[row[0]] = row[1]

        # Collect papers to embed
        from scholaraio.papers import iter_paper_dirs, read_meta

        to_embed: list[tuple[str, str, str]] = []  # (paper_id, text, hash)
        for pdir in iter_paper_dirs(papers_dir):
            try:
                meta = read_meta(pdir)
            except (ValueError, FileNotFoundError) as e:
                _log.debug("failed to read meta.json in %s: %s", pdir.name, e)
                continue
            paper_id = meta.get("id") or pdir.name

            title = (meta.get("title") or "").strip()
            abstract = (meta.get("abstract") or "").strip()
            if not title and not abstract:
                continue

            h = _content_hash(title, abstract)
            if not rebuild and existing_hashes.get(paper_id) == h:
                continue  # content unchanged, skip

            if not abstract:
                _log.debug("no abstract, embedding title only: %s", paper_id)

            parts = [p for p in [title, abstract] if p]
            text = "\n\n".join(parts)
            to_embed.append((paper_id, text, h))

        if not to_embed:
            return 0

        _log.info("embedding %d papers", len(to_embed))
        texts = [t for _, t, _ in to_embed]
        vecs = _embed_batch(texts, cfg)

        new_ids = []
        new_vecs_raw = []
        updated_ids = set()
        for (paper_id, _, h), vec in zip(to_embed, vecs):
            is_update = paper_id in existing_hashes
            conn.execute(
                "INSERT OR REPLACE INTO paper_vectors "
                "(paper_id, embedding, content_hash) VALUES (?, ?, ?)",
                (paper_id, _pack(vec), h),
            )
            new_ids.append(paper_id)
            new_vecs_raw.append(vec)
            if is_update:
                updated_ids.add(paper_id)

        conn.commit()
    finally:
        conn.close()

    if to_embed:
        if updated_ids:
            # Content changed for existing papers — must rebuild FAISS
            _invalidate_faiss(db_path)
        else:
            # Pure additions — try incremental append
            _append_faiss(db_path, new_ids, new_vecs_raw)

    return len(to_embed)


# ============================================================================
#  Search
# ============================================================================


def _build_faiss_from_db(
    db_path: Path,
    index_path: Path,
    ids_path: Path,
    *,
    empty_msg: str = "向量索引为空，请先运行 `scholaraio embed`",
) -> tuple["faiss.Index", list[str]]:
    """Build or load a FAISS IndexFlatIP from a paper_vectors table.

    Generic implementation that works with any SQLite DB containing a
    ``paper_vectors`` table (main library or explore silo).

    Args:
        db_path: SQLite database with ``paper_vectors`` table.
        index_path: Path to cached ``faiss.index`` file.
        ids_path: Path to cached ``faiss_ids.json`` file.
        empty_msg: Error message when no vectors found.

    Returns:
        ``(faiss_index, paper_ids)`` tuple.

    Raises:
        FileNotFoundError: No vectors in the database.
    """
    import faiss
    import numpy as np

    if index_path.exists() and ids_path.exists():
        index = faiss.read_index(str(index_path))
        paper_ids = json.loads(ids_path.read_text("utf-8"))
        return index, paper_ids

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT paper_id, embedding FROM paper_vectors"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise FileNotFoundError(empty_msg)

    # Validate blob dimensions: use first row to determine dim, skip corrupted rows
    expected_blob_len = len(rows[0][1])
    dim = expected_blob_len // 4
    if expected_blob_len == 0 or expected_blob_len % 4 != 0:
        raise ValueError(f"First embedding blob has invalid length: {expected_blob_len}")

    valid_rows = []
    for r in rows:
        if len(r[1]) != expected_blob_len:
            _log.warning("Skipping paper %s: blob length %d != expected %d",
                         r[0], len(r[1]), expected_blob_len)
            continue
        valid_rows.append(r)

    if not valid_rows:
        raise FileNotFoundError("No valid embedding rows after dimension check")

    paper_ids = [r[0] for r in valid_rows]
    vecs = np.array(
        [list(struct.unpack(f"{dim}f", r[1])) for r in valid_rows],
        dtype="float32",
    )
    faiss.normalize_L2(vecs)

    index = faiss.IndexFlatIP(dim)
    index.add(vecs)

    faiss.write_index(index, str(index_path))
    ids_path.write_text(
        json.dumps(paper_ids, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return index, paper_ids


def _build_faiss_index(db_path: Path) -> tuple["faiss.Index", list[str]]:
    """Build or load a FAISS IndexFlatIP for the main library."""
    idx_p, ids_p = _faiss_paths(db_path)
    return _build_faiss_from_db(db_path, idx_p, ids_p)


def _vsearch_faiss(
    query: str,
    index: "faiss.Index",
    paper_ids: list[str],
    top_k: int,
    cfg: Config | None = None,
) -> list[tuple[str, float]]:
    """Run a FAISS similarity search, returning ``(paper_id, score)`` pairs.

    Args:
        query: Natural-language query text.
        index: FAISS ``IndexFlatIP`` instance.
        paper_ids: Paper ID list aligned with the index.
        top_k: Number of results to return.
        cfg: Optional config for embedding model.

    Returns:
        List of ``(paper_id, score)`` sorted by descending similarity.
    """
    import faiss
    import numpy as np

    q_vec = np.array([_embed_text(query, cfg)], dtype="float32")
    faiss.normalize_L2(q_vec)

    fetch_k = min(top_k, index.ntotal)
    scores, indices = index.search(q_vec, fetch_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        results.append((paper_ids[idx], float(score)))
    return results


def vsearch(
    query: str,
    db_path: Path,
    top_k: int | None = None,
    cfg: Config | None = None,
    *,
    year: str | None = None,
    journal: str | None = None,
    paper_type: str | None = None,
    paper_ids: set[str] | None = None,
) -> list[dict]:
    """语义向量检索，使用 FAISS 加速余弦相似度搜索。

    将查询文本编码为向量，通过 FAISS IndexFlatIP 检索最相似的论文。
    FAISS 索引在首次查询时自动构建并缓存到磁盘，向量变更后自动失效重建。

    Args:
        query: 自然语言查询文本。
        db_path: SQLite 数据库路径（需包含 ``paper_vectors`` 表）。
        top_k: 最多返回条数，为 ``None`` 时从 ``cfg.embed.top_k`` 读取。
        cfg: 可选的 :class:`~scholaraio.config.Config`，用于加载嵌入模型。
        year: 年份过滤（``"2023"`` / ``"2020-2024"`` / ``"2020-"``）。
        journal: 期刊名过滤（LIKE 模糊匹配）。
        paper_type: 论文类型过滤（如 ``"review"``、``"journal-article"``）。
        paper_ids: 论文 UUID 白名单，仅返回集合内的结果。

    Returns:
        论文字典列表，按 ``score`` 降序排列。每项包含
        ``paper_id``, ``title``, ``authors``, ``year``, ``journal``, ``score``。

    Raises:
        FileNotFoundError: 索引文件或 ``paper_vectors`` 表不存在。
    """
    import faiss
    import numpy as np

    if top_k is None:
        top_k = cfg.embed.top_k if cfg is not None else 10

    if not db_path.exists():
        raise FileNotFoundError(
            f"索引文件不存在：{db_path}\n请先运行 `scholaraio index`"
        )

    conn = sqlite3.connect(db_path)
    try:
        has_vectors = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='paper_vectors'"
        ).fetchone()
        if not has_vectors:
            raise FileNotFoundError(
                "向量索引不存在，请先运行 `scholaraio embed`"
            )
    finally:
        conn.close()

    index, faiss_ids = _build_faiss_index(db_path)

    q_vec = np.array([_embed_text(query, cfg)], dtype="float32")
    faiss.normalize_L2(q_vec)

    # Fetch more candidates when post-filtering is needed
    fetch_k = top_k * 5 if (year or journal or paper_type or paper_ids) else top_k
    fetch_k = min(fetch_k, index.ntotal)
    scores, indices = index.search(q_vec, fetch_k)

    # Load metadata from FTS5 table
    conn = sqlite3.connect(db_path)
    try:
        has_fts = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='papers'"
        ).fetchone()
        meta_map: dict[str, dict] = {}
        if has_fts:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(
                "SELECT paper_id, title, authors, year, journal, citation_count, paper_type FROM papers"
            ).fetchall():
                meta_map[row["paper_id"]] = dict(row)
        # Load dir_name mapping
        dir_map: dict[str, str] = {}
        has_reg = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='papers_registry'"
        ).fetchone()
        if has_reg:
            for row in conn.execute("SELECT id, dir_name FROM papers_registry").fetchall():
                dir_map[row[0]] = row[1]
    finally:
        conn.close()

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        pid = faiss_ids[idx]
        meta = meta_map.get(pid, {})
        results.append({
            "paper_id": pid,
            "dir_name": dir_map.get(pid, ""),
            "title": meta.get("title") or pid,
            "authors": meta.get("authors") or "",
            "year": meta.get("year") or "",
            "journal": meta.get("journal") or "",
            "citation_count": meta.get("citation_count") or "",
            "paper_type": meta.get("paper_type") or "",
            "score": float(score),
        })

    if paper_ids is not None:
        results = [r for r in results if r["paper_id"] in paper_ids]
    if year or journal or paper_type:
        results = _post_filter(results, year=year, journal=journal, paper_type=paper_type)

    return results[:top_k]


def _safe_year(r: dict) -> int | None:
    """Extract year as int, return None if missing or invalid."""
    val = r.get("year", "")
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _post_filter(
    results: list[dict],
    *,
    year: str | None = None,
    journal: str | None = None,
    paper_type: str | None = None,
) -> list[dict]:
    """对向量检索结果做年份/期刊/类型过滤。"""
    from scholaraio.papers import parse_year_range

    filtered = results
    if year:
        start_i, end_i = parse_year_range(year)
        if start_i is not None and end_i is not None:
            filtered = [r for r in filtered
                        if _safe_year(r) is not None and start_i <= _safe_year(r) <= end_i]
        elif start_i is not None:
            filtered = [r for r in filtered
                        if _safe_year(r) is not None and _safe_year(r) >= start_i]
        elif end_i is not None:
            filtered = [r for r in filtered
                        if _safe_year(r) is not None and _safe_year(r) <= end_i]
    if journal:
        j_lower = journal.lower()
        filtered = [r for r in filtered if j_lower in str(r.get("journal", "")).lower()]
    if paper_type:
        t_lower = paper_type.lower()
        filtered = [r for r in filtered if t_lower in str(r.get("paper_type", "")).lower()]
    return filtered


# ============================================================================
#  Section-level chunks
# ============================================================================

_CHUNKS_SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_chunks (
    chunk_id     TEXT PRIMARY KEY,
    paper_id     TEXT NOT NULL,
    section_title TEXT NOT NULL DEFAULT '',
    section_type TEXT NOT NULL DEFAULT 'other',
    chunk_text   TEXT NOT NULL,
    embedding    BLOB NOT NULL,
    content_hash TEXT NOT NULL DEFAULT ''
);
"""

_SECTION_TYPE_MAP = {
    "introduction": "introduction",
    "background": "introduction",
    "related work": "related_work",
    "literature review": "related_work",
    "method": "methods",
    "methods": "methods",
    "methodology": "methods",
    "materials and methods": "methods",
    "experimental": "methods",
    "experiment": "methods",
    "experimental section": "methods",
    "result": "results",
    "results": "results",
    "results and discussion": "results",
    "findings": "results",
    "discussion": "discussion",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "concluding remarks": "conclusion",
    "summary": "conclusion",
    "abstract": "abstract",
    "acknowledgment": "other",
    "acknowledgments": "other",
    "acknowledgements": "other",
    "references": "references",
    "supporting information": "other",
    "supplementary": "other",
    "data availability": "other",
}


def _classify_section(title: str) -> str:
    """Classify a section title into a canonical type."""
    t = title.strip().lower()
    # Direct match
    if t in _SECTION_TYPE_MAP:
        return _SECTION_TYPE_MAP[t]
    # Partial match
    for key, val in _SECTION_TYPE_MAP.items():
        if key in t:
            return val
    return "other"


def _chunk_hash(paper_id: str, section_title: str, text: str) -> str:
    """Content hash for a chunk to detect changes."""
    s = f"{paper_id}:{section_title}:{text}"
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:12]


_SUBSECTION_RE = re.compile(r"^(#{2,6})\s+(.+)", re.MULTILINE)

# Thresholds for sub-splitting
_MAX_CHUNK_CHARS = 2000
_WINDOW_CHARS = 1500
_OVERLAP_CHARS = 300


def _subsplit_section(
    title: str, level: int, start_line: int, text: str,
) -> list[dict]:
    """Split a single section into sub-chunks when it is too large.

    Strategy:
    1. If the section contains markdown sub-headings (## or deeper), split
       at those boundaries.  Each sub-chunk inherits the parent section_type
       and gets a composite title like "Methods > 2.1 Cell Culture".
    2. Any resulting piece that still exceeds ``_MAX_CHUNK_CHARS`` and has
       no further sub-headings is split by paragraph boundaries using a
       sliding window (``_WINDOW_CHARS`` with ``_OVERLAP_CHARS`` overlap).
    3. Sections shorter than ``_MAX_CHUNK_CHARS`` are returned as-is.

    Returns a list of dicts with ``title``, ``level``, ``start_line``,
    ``text``, and ``sub_idx`` (int, 0-based within the parent section).
    """
    # Short section — return as single chunk
    if len(text) <= _MAX_CHUNK_CHARS:
        return [{"title": title, "level": level,
                 "start_line": start_line, "text": text, "sub_idx": 0}]

    # --- Step 1: try sub-heading split ---
    sub_matches = list(_SUBSECTION_RE.finditer(text))
    if sub_matches:
        pieces: list[dict] = []
        # Text before the first sub-heading
        pre_text = text[:sub_matches[0].start()].strip()
        if len(pre_text) >= 50:
            pieces.append({
                "title": title,
                "level": level,
                "start_line": start_line,
                "text": pre_text,
                "sub_idx": 0,
            })

        for j, m in enumerate(sub_matches):
            sub_title_raw = m.group(2).strip()
            end_pos = sub_matches[j + 1].start() if j + 1 < len(sub_matches) else len(text)
            body = text[m.end():end_pos].strip()
            if len(body) < 50:
                continue
            pieces.append({
                "title": f"{title} > {sub_title_raw}",
                "level": level + len(m.group(1)) - 1,
                "start_line": start_line,
                "text": body,
                "sub_idx": len(pieces),
            })

        # Step 2: recursively handle still-oversized pieces (paragraph window)
        final: list[dict] = []
        for p in pieces:
            if len(p["text"]) <= _MAX_CHUNK_CHARS:
                p["sub_idx"] = len(final)
                final.append(p)
            else:
                for win in _paragraph_window(p["text"]):
                    final.append({
                        "title": p["title"],
                        "level": p["level"],
                        "start_line": p["start_line"],
                        "text": win,
                        "sub_idx": len(final),
                    })
        return final if final else [{"title": title, "level": level,
                                      "start_line": start_line, "text": text,
                                      "sub_idx": 0}]

    # --- No sub-headings but text is long: paragraph-window split ---
    windows = _paragraph_window(text)
    return [
        {"title": title, "level": level, "start_line": start_line,
         "text": w, "sub_idx": i}
        for i, w in enumerate(windows)
    ]


def _paragraph_window(text: str) -> list[str]:
    """Split long text into overlapping windows at paragraph boundaries.

    Paragraphs are detected by blank-line boundaries (``\\n\\n``).
    Each window targets ``_WINDOW_CHARS`` with ``_OVERLAP_CHARS`` overlap.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return [text]

    windows: list[str] = []
    buf: list[str] = []
    buf_len = 0

    for para in paragraphs:
        buf.append(para)
        buf_len += len(para) + 2  # approximate \n\n join

        if buf_len >= _WINDOW_CHARS:
            windows.append("\n\n".join(buf))
            # Keep tail paragraphs for overlap
            overlap_buf: list[str] = []
            overlap_len = 0
            for p in reversed(buf):
                if overlap_len + len(p) > _OVERLAP_CHARS:
                    break
                overlap_buf.insert(0, p)
                overlap_len += len(p) + 2
            buf = overlap_buf
            buf_len = overlap_len

    if buf:
        # Avoid a tiny trailing window — merge into the last one
        tail = "\n\n".join(buf)
        if windows and len(tail) < 200:
            windows[-1] = windows[-1] + "\n\n" + tail
        else:
            windows.append(tail)

    return windows if windows else [text]


def _split_by_toc(lines: list[str], toc: list[dict]) -> list[dict]:
    """Split paper text into sections using TOC entries, with sub-splitting.

    Each TOC entry has ``line`` (1-indexed), ``level``, ``title``.
    Returns list of dicts with ``title``, ``level``, ``start_line``, ``text``,
    and ``sub_idx`` (sub-chunk index within the parent section).
    """
    if not toc:
        return []

    sections = []
    for i, entry in enumerate(toc):
        start = entry["line"]  # 1-indexed
        if i + 1 < len(toc):
            end = toc[i + 1]["line"]
        else:
            end = len(lines) + 1

        # Extract text between this header and the next, skip the header line itself
        body_lines = lines[start:end - 1]  # start is 1-indexed, so lines[start] = line after header
        text = "\n".join(body_lines).strip()

        if len(text) < 50:  # Skip very short sections (acknowledgments, etc.)
            continue

        # Sub-split large sections
        sub_chunks = _subsplit_section(entry["title"], entry.get("level", 1), start, text)
        sections.extend(sub_chunks)

    return sections


def build_chunks(
    papers_dir: Path,
    db_path: Path,
    rebuild: bool = False,
    cfg: Config | None = None,
) -> int:
    """Build section-level chunks from papers with TOC.

    Reads TOC from meta.json, splits paper.md by section boundaries,
    classifies section types, embeds each chunk, and stores in
    ``paper_chunks`` table.

    Args:
        papers_dir: Ingested papers directory.
        db_path: SQLite database path.
        rebuild: Clear all chunks before rebuilding.
        cfg: Optional config.

    Returns:
        Number of new chunks written.
    """
    from scholaraio.papers import iter_paper_dirs, read_meta

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(_CHUNKS_SCHEMA)

        if rebuild:
            conn.execute("DELETE FROM paper_chunks")
            conn.commit()

        # Existing chunk hashes for incremental
        existing: set[str] = set()
        if not rebuild:
            for row in conn.execute("SELECT chunk_id FROM paper_chunks").fetchall():
                existing.add(row[0])

        # Process papers one at a time to avoid OOM.
        # Each paper's sections are embedded immediately, then memory freed.
        BATCH = 50  # embed batch size within a single paper's chunks
        total_written = 0
        paper_count = 0

        for pdir in iter_paper_dirs(papers_dir):
            try:
                meta = read_meta(pdir)
            except (ValueError, FileNotFoundError):
                continue

            paper_id = meta.get("id") or pdir.name
            toc = meta.get("toc")
            if not toc:
                continue

            md_path = pdir / "paper.md"
            if not md_path.exists():
                continue

            lines = md_path.read_text(encoding="utf-8", errors="replace").splitlines()
            sections = _split_by_toc(lines, toc)

            # Collect this paper's new chunks
            paper_chunks: list[tuple[str, str, str, str, str]] = []
            for sec in sections:
                section_type = _classify_section(sec["title"])
                if section_type == "references":
                    continue

                sub_idx = sec.get("sub_idx", 0)
                chunk_id = f"{paper_id}::{sec['start_line']}:{sub_idx}"

                if chunk_id in existing:
                    continue

                paper_chunks.append((
                    chunk_id, paper_id, sec["title"], section_type, sec["text"]
                ))

            if not paper_chunks:
                continue

            # Embed and write this paper's chunks in small batches
            for batch_start in range(0, len(paper_chunks), BATCH):
                batch = paper_chunks[batch_start:batch_start + BATCH]
                texts = [t[:1000] for _, _, _, _, t in batch]
                vecs = _embed_batch(texts, cfg)

                for (chunk_id, pid, title, stype, text), vec in zip(batch, vecs):
                    h = _chunk_hash(pid, title, text)
                    conn.execute(
                        "INSERT OR REPLACE INTO paper_chunks "
                        "(chunk_id, paper_id, section_title, section_type, chunk_text, embedding, content_hash) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (chunk_id, pid, title, stype, text, _pack(vec), h),
                    )

                total_written += len(batch)

            conn.commit()  # Commit per paper for crash safety
            paper_count += 1

            if paper_count % 50 == 0:
                _log.info("  processed %d papers, %d chunks so far",
                          paper_count, total_written)

            # Free memory for this paper
            del lines, sections, paper_chunks

        if total_written == 0:
            return 0

        _log.info("embedding complete: %d chunks from %d papers",
                  total_written, paper_count)
    finally:
        conn.close()

    # Invalidate chunk FAISS cache
    chunk_idx = db_path.parent / "faiss_chunks.index"
    chunk_ids = db_path.parent / "faiss_chunks_ids.json"
    for f in (chunk_idx, chunk_ids):
        if f.exists():
            f.unlink()

    return total_written


def _build_chunk_faiss(db_path: Path) -> tuple["faiss.Index", list[str]]:
    """Build or load FAISS index for paper_chunks table."""
    import faiss
    import numpy as np

    idx_path = db_path.parent / "faiss_chunks.index"
    ids_path = db_path.parent / "faiss_chunks_ids.json"

    if idx_path.exists() and ids_path.exists():
        index = faiss.read_index(str(idx_path))
        chunk_ids = json.loads(ids_path.read_text("utf-8"))
        return index, chunk_ids

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT chunk_id, embedding FROM paper_chunks"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise FileNotFoundError("No chunks found. Run `scholaraio chunks` first.")

    expected_len = len(rows[0][1])
    dim = expected_len // 4
    valid = [(r[0], r[1]) for r in rows if len(r[1]) == expected_len]

    if not valid:
        raise FileNotFoundError("No valid chunk embeddings")

    chunk_ids = [r[0] for r in valid]
    vecs = np.array(
        [list(struct.unpack(f"{dim}f", r[1])) for r in valid],
        dtype="float32",
    )
    faiss.normalize_L2(vecs)

    index = faiss.IndexFlatIP(dim)
    index.add(vecs)

    faiss.write_index(index, str(idx_path))
    ids_path.write_text(json.dumps(chunk_ids, ensure_ascii=False) + "\n", "utf-8")
    return index, chunk_ids


def csearch(
    query: str,
    db_path: Path,
    top_k: int | None = None,
    cfg: Config | None = None,
    *,
    section_type: str | None = None,
    paper_ids: set[str] | None = None,
) -> list[dict]:
    """Section-level semantic search across paper chunks.

    Args:
        query: Natural language query.
        db_path: SQLite database path.
        top_k: Max results.
        cfg: Optional config.
        section_type: Filter by section type (introduction/methods/results/discussion/conclusion).
        paper_ids: Paper UUID whitelist.

    Returns:
        List of chunk dicts with paper_id, section_title, section_type,
        snippet, score.
    """
    import faiss
    import numpy as np

    if top_k is None:
        top_k = cfg.embed.top_k if cfg is not None else 10

    index, chunk_ids = _build_chunk_faiss(db_path)

    q_vec = np.array([_embed_text(query, cfg)], dtype="float32")
    faiss.normalize_L2(q_vec)

    fetch_k = min(top_k * 5, index.ntotal)  # Over-fetch for post-filtering
    scores, indices = index.search(q_vec, fetch_k)

    # Load chunk metadata
    conn = sqlite3.connect(db_path)
    try:
        chunk_meta: dict[str, dict] = {}
        for row in conn.execute(
            "SELECT chunk_id, paper_id, section_title, section_type, "
            "substr(chunk_text, 1, 300) FROM paper_chunks"
        ).fetchall():
            chunk_meta[row[0]] = {
                "chunk_id": row[0],
                "paper_id": row[1],
                "section_title": row[2],
                "section_type": row[3],
                "snippet": row[4],
            }

        # Enrich with paper metadata
        paper_meta: dict[str, dict] = {}
        has_reg = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='papers_registry'"
        ).fetchone()
        if has_reg:
            for row in conn.execute(
                "SELECT id, dir_name FROM papers_registry"
            ).fetchall():
                paper_meta[row[0]] = {"dir_name": row[1]}

        has_fts = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='papers'"
        ).fetchone()
        if has_fts:
            for row in conn.execute(
                "SELECT paper_id, title, authors, year, journal FROM papers"
            ).fetchall():
                if row[0] in paper_meta:
                    paper_meta[row[0]].update({
                        "paper_title": row[1], "authors": row[2],
                        "year": row[3], "journal": row[4],
                    })
                else:
                    paper_meta[row[0]] = {
                        "paper_title": row[1], "authors": row[2],
                        "year": row[3], "journal": row[4],
                    }
    finally:
        conn.close()

    results = []
    seen_papers: set[str] = set()
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        cid = chunk_ids[idx]
        cm = chunk_meta.get(cid)
        if not cm:
            continue

        pid = cm["paper_id"]

        # Filters
        if section_type and cm["section_type"] != section_type:
            continue
        if paper_ids and pid not in paper_ids:
            continue

        pm = paper_meta.get(pid, {})
        results.append({
            **cm,
            "dir_name": pm.get("dir_name", ""),
            "paper_title": pm.get("paper_title", ""),
            "authors": pm.get("authors", ""),
            "year": pm.get("year", ""),
            "journal": pm.get("journal", ""),
            "score": float(score),
        })

        if len(results) >= top_k:
            break

    return results
