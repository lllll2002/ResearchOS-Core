from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_ROOT = Path(os.environ.get("RESEARCH_OS_VAULT", PROJECT_ROOT / "vault"))
BRIDGE_ROOT = VAULT_ROOT / ".ai-bridge"
TASKS_DIR = BRIDGE_ROOT / "tasks"
RESULTS_DIR = BRIDGE_ROOT / "results"
WORKSPACE_DIR = PROJECT_ROOT / "workspace"
OUTPUT_JSON = WORKSPACE_DIR / "bridge-panel-data.json"
LOG_ROOT = PROJECT_ROOT / "workspace" / "codex-temp"

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
KEY_VALUE_RE = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*)$")
TASK_ID_RE = re.compile(r"TASK-\d+")


@dataclass
class BridgeFile:
    path: Path
    frontmatter: dict[str, Any]
    body: str
    raw: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "~", "null", "None"}:
        return None
    if value == "[]":
        return []
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    block = match.group(1)
    body = text[match.end():]
    data: dict[str, Any] = {}
    current_list_key: str | None = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line.lstrip().startswith("- ") and current_list_key:
            data.setdefault(current_list_key, []).append(line.split("-", 1)[1].strip())
            continue
        key_match = KEY_VALUE_RE.match(line)
        if not key_match:
            current_list_key = None
            continue
        key = key_match.group("key")
        value = key_match.group("value")
        parsed = parse_scalar(value)
        if parsed == []:
            data[key] = []
            current_list_key = key
        elif parsed is None and value.strip() == "":
            data[key] = []
            current_list_key = key
        else:
            data[key] = parsed
            current_list_key = None
    return data, body


def load_bridge_file(path: Path) -> BridgeFile:
    raw = read_text(path)
    frontmatter, body = parse_frontmatter(raw)
    return BridgeFile(path=path, frontmatter=frontmatter, body=body, raw=raw)


def task_id_from_path(path: Path) -> str:
    match = TASK_ID_RE.search(path.name)
    return match.group(0) if match else path.stem


def summarize_markdown(body: str, max_lines: int = 6) -> list[str]:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    return lines[:max_lines]


def latest_log_for_task(task_id: str) -> Path | None:
    if not LOG_ROOT.exists():
        return None
    logs = sorted(LOG_ROOT.glob(f"{task_id}-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def parse_log(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    text = read_text(path)
    lines = text.splitlines()
    returncode = None
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    section: str | None = None
    for line in lines:
        if line.startswith("returncode:"):
            try:
                returncode = int(line.split(":", 1)[1].strip())
            except ValueError:
                returncode = None
        elif line == "stdout:":
            section = "stdout"
        elif line == "stderr:":
            section = "stderr"
        elif section == "stdout":
            stdout_lines.append(line)
        elif section == "stderr":
            stderr_lines.append(line)
    return {
        "path": str(path),
        "updated": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "returncode": returncode,
        "stdout_preview": [line for line in stdout_lines if line.strip()][:12],
        "stderr_preview": [line for line in stderr_lines if line.strip()][:18],
        "tail": [line for line in lines[-30:] if line.strip()],
    }


def result_for_task(task_id: str) -> BridgeFile | None:
    path = RESULTS_DIR / f"{task_id}-result.md"
    if path.exists():
        return load_bridge_file(path)
    return None


def collect_item(task_path: Path) -> dict[str, Any]:
    task = load_bridge_file(task_path)
    task_id = str(task.frontmatter.get("id") or task_id_from_path(task_path))
    result = result_for_task(task_id)
    log = parse_log(latest_log_for_task(task_id))

    result_status = None
    result_summary: list[str] = []
    result_path = None
    if result:
        fm = result.frontmatter
        result_status = fm.get("status") or fm.get("task_status")
        result_path = str(result.path)
        result_summary = summarize_markdown(result.body)
        if not result_status:
            if "task_id" in fm:
                result_status = fm.get("status")
            elif fm.get("id") == task_id:
                result_status = fm.get("status")

    allowed = task.frontmatter.get("allowed_write_paths") or []
    expected = task.frontmatter.get("expected_output") or []
    inputs = task.frontmatter.get("inputs") or []

    stage = "pending"
    task_status = str(task.frontmatter.get("status") or "unknown")
    if task_status == "pending":
        stage = "queued"
    elif task_status == "in_progress":
        stage = "running"
    elif task_status == "done":
        stage = "done"
    elif task_status == "blocked":
        stage = "blocked"

    if result_status == "done":
        stage = "done"
        task_status = "done"
    elif log and log.get("returncode") not in (None, 0) and task_status != "done":
        stage = "error"

    return {
        "task_id": task_id,
        "task_path": str(task.path),
        "title": task.path.stem,
        "status": task_status,
        "stage": stage,
        "scope": task.frontmatter.get("scope"),
        "created": task.frontmatter.get("created"),
        "deadline": task.frontmatter.get("deadline"),
        "inputs": inputs,
        "allowed_write_paths": allowed,
        "expected_output": expected,
        "task_summary": summarize_markdown(task.body),
        "result_status": result_status,
        "result_path": result_path,
        "result_summary": result_summary,
        "log": log,
        "updated": datetime.fromtimestamp(task.path.stat().st_mtime).isoformat(timespec="seconds"),
    }


def build_snapshot(limit: int) -> dict[str, Any]:
    task_paths = sorted(
        [p for p in TASKS_DIR.glob("TASK-*.md") if p.name != "TASK_TEMPLATE.md"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    items = [collect_item(path) for path in task_paths[:limit]]
    counts = {
        "queued": sum(1 for item in items if item["stage"] == "queued"),
        "running": sum(1 for item in items if item["stage"] == "running"),
        "done": sum(1 for item in items if item["stage"] == "done"),
        "blocked": sum(1 for item in items if item["stage"] in {"blocked", "error"}),
    }
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "counts": counts,
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate bridge panel snapshot data.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output", default=str(OUTPUT_JSON))
    args = parser.parse_args()

    snapshot = build_snapshot(args.limit)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
