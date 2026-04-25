from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_ROOT = Path(os.environ.get("RESEARCH_OS_VAULT", PROJECT_ROOT / "vault"))
BRIDGE_ROOT = VAULT_ROOT / ".ai-bridge"
TASKS_DIR = BRIDGE_ROOT / "tasks"
RESULTS_DIR = BRIDGE_ROOT / "results"
EVENTS_DIR = BRIDGE_ROOT / "events"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    block = text[4:end]
    body = text[end + 5:]
    data: dict[str, Any] = {}
    current_key: str | None = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line.lstrip().startswith("- ") and current_key:
            data.setdefault(current_key, []).append(line.split("-", 1)[1].strip())
            continue
        if ":" not in line:
            current_key = None
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value in {"", "[]"}:
            data[key] = []
            current_key = key
        elif value in {"~", "null", "None"}:
            data[key] = None
            current_key = None
        else:
            data[key] = value
            current_key = None
    return data, body


def latest_event(task_id: str) -> Path | None:
    matches = sorted(EVENTS_DIR.glob(f"{task_id}-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def item_for_task(path: Path) -> dict[str, Any]:
    fm, _ = parse_frontmatter(read_text(path))
    task_id = fm.get("id") or path.stem.split("-")[0]
    result = RESULTS_DIR / f"{task_id}-result.md"
    event = latest_event(str(task_id))
    return {
        "task_id": task_id,
        "task_path": str(path),
        "status": fm.get("status"),
        "scope": fm.get("scope"),
        "result_path": str(result) if result.exists() else None,
        "event_path": str(event) if event else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Query current ai-bridge task/result/event status.")
    parser.add_argument("--task-id")
    args = parser.parse_args()

    task_paths = sorted(p for p in TASKS_DIR.glob("TASK-*.md") if p.name != "TASK_TEMPLATE.md")
    items = [item_for_task(path) for path in task_paths]
    if args.task_id:
        items = [item for item in items if item["task_id"] == args.task_id]
    print(json.dumps({"items": items}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
