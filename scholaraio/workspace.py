"""
workspace.py — 工作区论文子集管理
===================================

每个工作区是 ``workspace/<name>/`` 目录，内含 ``papers.json`` 索引文件
指向 ``data/papers/`` 中的论文。工作区内可自由存放笔记、代码、草稿等。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

_log = logging.getLogger(__name__)


# ============================================================================
#  Internal helpers
# ============================================================================

def _papers_json(ws_dir: Path) -> Path:
    return ws_dir / "papers.json"


def _read(ws_dir: Path) -> list[dict]:
    pj = _papers_json(ws_dir)
    if not pj.exists():
        return []
    return json.loads(pj.read_text(encoding="utf-8"))


def _write(ws_dir: Path, entries: list[dict]) -> None:
    _papers_json(ws_dir).write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ============================================================================
#  Public API
# ============================================================================

def create(ws_dir: Path) -> Path:
    """创建工作区目录并初始化空 papers.json。

    Args:
        ws_dir: 工作区目录路径。

    Returns:
        papers.json 文件路径。
    """
    ws_dir.mkdir(parents=True, exist_ok=True)
    pj = _papers_json(ws_dir)
    if not pj.exists():
        _write(ws_dir, [])
    return pj


def add(ws_dir: Path, paper_refs: list[str], db_path: Path) -> list[dict]:
    """添加论文到工作区。

    通过 UUID、目录名或 DOI 解析论文，去重后追加到 papers.json。

    Args:
        ws_dir: 工作区目录路径。
        paper_refs: 论文引用列表（UUID / 目录名 / DOI）。
        db_path: index.db 路径，用于 lookup_paper。

    Returns:
        新增条目列表。
    """
    from scholaraio.index import lookup_paper

    entries = _read(ws_dir)
    existing_ids = {e["id"] for e in entries}
    added: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    for ref in paper_refs:
        record = lookup_paper(db_path, ref)
        if record is None:
            _log.warning("无法解析论文引用: %s", ref)
            continue
        uid = record["id"]
        if uid in existing_ids:
            _log.debug("已存在，跳过: %s", ref)
            continue
        entry = {"id": uid, "dir_name": record["dir_name"], "added_at": now}
        entries.append(entry)
        existing_ids.add(uid)
        added.append(entry)

    if added:
        _write(ws_dir, entries)
    return added


def remove(ws_dir: Path, paper_refs: list[str], db_path: Path) -> list[dict]:
    """从工作区移除论文。

    Args:
        ws_dir: 工作区目录路径。
        paper_refs: 论文引用列表（UUID / 目录名 / DOI）。
        db_path: index.db 路径。

    Returns:
        被移除的条目列表。
    """
    from scholaraio.index import lookup_paper

    entries = _read(ws_dir)
    remove_ids: set[str] = set()
    for ref in paper_refs:
        record = lookup_paper(db_path, ref)
        if record:
            remove_ids.add(record["id"])
        else:
            # Try direct UUID match
            remove_ids.add(ref)

    removed = [e for e in entries if e["id"] in remove_ids]
    if removed:
        entries = [e for e in entries if e["id"] not in remove_ids]
        _write(ws_dir, entries)
    return removed


def list_workspaces(ws_root: Path) -> list[str]:
    """列出所有含 papers.json 的工作区。

    Args:
        ws_root: workspace/ 根目录。

    Returns:
        工作区名称列表（排序）。
    """
    if not ws_root.is_dir():
        return []
    return sorted(
        d.name for d in ws_root.iterdir()
        if d.is_dir() and _papers_json(d).exists()
    )


def show(ws_dir: Path, db_path: Path) -> list[dict]:
    """查看工作区论文列表，刷新过期的 dir_name。

    Args:
        ws_dir: 工作区目录路径。
        db_path: index.db 路径。

    Returns:
        论文条目列表（含最新 dir_name）。
    """
    from scholaraio.index import lookup_paper

    entries = _read(ws_dir)
    changed = False
    for e in entries:
        record = lookup_paper(db_path, e["id"])
        if record and record["dir_name"] != e.get("dir_name"):
            e["dir_name"] = record["dir_name"]
            changed = True
    if changed:
        _write(ws_dir, entries)
    return entries


def read_paper_ids(ws_dir: Path) -> set[str]:
    """返回工作区中所有论文的 UUID 集合。

    Args:
        ws_dir: 工作区目录路径。

    Returns:
        UUID 字符串集合，用于搜索过滤。
    """
    return {e["id"] for e in _read(ws_dir)}


def read_dir_names(ws_dir: Path, db_path: Path) -> set[str]:
    """返回工作区中所有论文的当前目录名集合。

    从 papers_registry 查找最新 dir_name（处理 rename 后的情况）。

    Args:
        ws_dir: 工作区目录路径。
        db_path: index.db 路径。

    Returns:
        目录名字符串集合，用于导出过滤。
    """
    from scholaraio.index import lookup_paper

    names: set[str] = set()
    for e in _read(ws_dir):
        record = lookup_paper(db_path, e["id"])
        if record:
            names.add(record["dir_name"])
        elif e.get("dir_name"):
            names.add(e["dir_name"])
    return names


# ============================================================================
#  Auto-assign papers to workspaces via LLM
# ============================================================================

_AUTO_ASSIGN_SYSTEM = """\
You are a research librarian. Given a paper's title and abstract, and a list of
existing workspaces with descriptions, assign the paper to 0-2 most relevant
workspaces. If the paper doesn't clearly fit any workspace, return an empty list.

Output ONLY a JSON object: {"workspaces": ["ws-name-1", "ws-name-2"]}
Use exact workspace names from the provided list. Return at most 2."""

_WS_DESCRIPTIONS = {
    "phase-separation": "LLPS, stress granules, condensates, electric field effects on phase separation, EHD, nucleation",
    "biocomputing": "DNA computing, molecular logic gates, synthetic biology circuits, biological computation",
    "multiscale-biocomputing": "Brain-computer interfaces, organoid computing, MEA neural recording, AI for neuroscience, multi-scale neural systems",
    "organoid-mea": "Organoids, MEA electrodes, FPGA neural interfaces, electrophysiology, neural recording hardware",
    "ai-neuro-theory": "AI neural theory, reservoir computing, neural network models, computational neuroscience",
    "misc-theory": "General theoretical work not fitting other categories",
}


def auto_assign(
    paper_id: str,
    title: str,
    abstract: str,
    ws_root: Path,
    db_path: Path,
    cfg: "Config",
) -> list[str]:
    """Use LLM to assign a paper to relevant workspaces.

    Args:
        paper_id: Paper UUID.
        title: Paper title.
        abstract: Paper abstract.
        ws_root: Workspace root directory.
        db_path: SQLite database path.
        cfg: Config with LLM settings.

    Returns:
        List of workspace names the paper was added to.
    """
    from scholaraio.metrics import call_llm

    # Build workspace list
    ws_list = []
    for ws_name in sorted(list_workspaces(ws_root)):
        desc = _WS_DESCRIPTIONS.get(ws_name, "")
        ws_list.append(f"- {ws_name}: {desc}")

    prompt = f"Paper title: {title}\nAbstract: {(abstract or '')[:500]}\n\nWorkspaces:\n" + "\n".join(ws_list)

    try:
        result = call_llm(prompt, cfg, system=_AUTO_ASSIGN_SYSTEM,
                          json_mode=True, max_tokens=100, purpose="ws_assign")
        resp = json.loads(result.content)
        assigned = resp.get("workspaces", [])
    except Exception as exc:
        _log.warning("Auto-assign failed: %s", exc)
        return []

    # Validate and add
    added = []
    available = set(list_workspaces(ws_root))
    for ws_name in assigned:
        if ws_name not in available:
            continue
        ws_dir = ws_root / ws_name
        # Check if already in workspace
        existing_ids = read_paper_ids(ws_dir)
        if paper_id in existing_ids:
            continue
        try:
            add(ws_dir, [paper_id], db_path)
            added.append(ws_name)
            _log.info("Auto-assigned %s to workspace '%s'", paper_id[:8], ws_name)
        except Exception as exc:
            _log.warning("Failed to add to '%s': %s", ws_name, exc)

    return added
