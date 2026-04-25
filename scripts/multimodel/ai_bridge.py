from __future__ import annotations

import argparse
import re
import shutil
from datetime import date
from pathlib import Path


import os
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_ROOT = Path(os.environ.get("RESEARCH_OS_VAULT", PROJECT_ROOT / "vault"))
BRIDGE_ROOT = PROJECT_ROOT / "workspace" / "ai-bridge"
TASKS_DIR = BRIDGE_ROOT / "tasks"
RESULTS_DIR = BRIDGE_ROOT / "results"
TASK_TEMPLATE = TASKS_DIR / "TASK_TEMPLATE.md"
RESULT_TEMPLATE = RESULTS_DIR / "RESULT_TEMPLATE.md"

TASK_STATUSES = {"pending", "in_progress", "done", "blocked"}
RESULT_STATUSES = {"done", "partial", "failed"}
OWNERS = {"claude", "codex", "human"}


def ensure_layout() -> None:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "task"


def task_path(task_id: str) -> Path | None:
    matches = sorted(TASKS_DIR.glob(f"{task_id}-*.md"))
    return matches[0] if matches else None


def result_path(task_id: str) -> Path:
    return RESULTS_DIR / f"{task_id}-result.md"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def set_frontmatter_value(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^({re.escape(key)}:\s*).*$")
    if pattern.search(text):
        return pattern.sub(lambda m: f"{m.group(1)}{value}", text, count=1)
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            insert_at = end + 4
            return text[:insert_at] + f"{key}: {value}\n" + text[insert_at:]
    raise ValueError(f"Could not find or insert key: {key}")


def create_task(owner: str, title: str) -> Path:
    if owner not in OWNERS:
        raise ValueError(f"owner must be one of: {', '.join(sorted(OWNERS))}")
    ensure_layout()
    template = read_text(TASK_TEMPLATE)
    existing_ids = []
    for path in TASKS_DIR.glob("TASK-*.md"):
        match = re.match(r"TASK-(\d+)", path.stem)
        if match:
            existing_ids.append(int(match.group(1)))
    next_id = max(existing_ids, default=0) + 1
    task_id = f"TASK-{next_id:03d}"
    filename = f"{task_id}-{slugify(title)}.md"
    content = template
    content = set_frontmatter_value(content, "id", task_id)
    content = set_frontmatter_value(content, "owner", owner)
    content = set_frontmatter_value(content, "created", date.today().isoformat())
    content = content.replace("Describe the concrete task in one paragraph.", title, 1)
    path = TASKS_DIR / filename
    write_text(path, content)
    return path


def update_task_status(task_id: str, status: str) -> Path:
    if status not in TASK_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(TASK_STATUSES))}")
    path = task_path(task_id)
    if path is None:
        raise FileNotFoundError(f"Task not found: {task_id}")
    content = read_text(path)
    content = set_frontmatter_value(content, "status", status)
    write_text(path, content)
    return path


def create_result(task_id: str, status: str) -> Path:
    if status not in RESULT_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(RESULT_STATUSES))}")
    ensure_layout()
    template = read_text(RESULT_TEMPLATE)
    content = template
    content = set_frontmatter_value(content, "task_id", task_id)
    content = set_frontmatter_value(content, "status", status)
    path = result_path(task_id)
    write_text(path, content)
    return path


def list_tasks(owner: str | None, status: str | None) -> list[Path]:
    paths = sorted(
        path
        for path in TASKS_DIR.glob("TASK-*.md")
        if path.name != TASK_TEMPLATE.name
    )
    if owner is None and status is None:
        return paths

    filtered: list[Path] = []
    for path in paths:
        text = read_text(path)
        owner_ok = owner is None or re.search(rf"(?m)^owner:\s*{re.escape(owner)}\s*$", text)
        status_ok = status is None or re.search(rf"(?m)^status:\s*{re.escape(status)}\s*$", text)
        if owner_ok and status_ok:
            filtered.append(path)
    return filtered


def archive_task(task_id: str) -> tuple[Path, Path | None]:
    path = task_path(task_id)
    if path is None:
        raise FileNotFoundError(f"Task not found: {task_id}")
    archive_dir = TASKS_DIR / "archive"
    archive_dir.mkdir(exist_ok=True)
    archived_task = archive_dir / path.name
    shutil.move(str(path), str(archived_task))

    result = result_path(task_id)
    archived_result = None
    if result.exists():
        results_archive = RESULTS_DIR / "archive"
        results_archive.mkdir(exist_ok=True)
        archived_result = results_archive / result.name
        shutil.move(str(result), str(archived_result))
    return archived_task, archived_result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage file-based AI bridge tasks.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_cmd = subparsers.add_parser("create-task", help="Create a task file from template.")
    create_cmd.add_argument("--owner", required=True, choices=sorted(OWNERS))
    create_cmd.add_argument("--title", required=True)

    update_cmd = subparsers.add_parser("set-task-status", help="Update a task status.")
    update_cmd.add_argument("--task-id", required=True)
    update_cmd.add_argument("--status", required=True, choices=sorted(TASK_STATUSES))

    result_cmd = subparsers.add_parser("create-result", help="Create a result file from template.")
    result_cmd.add_argument("--task-id", required=True)
    result_cmd.add_argument("--status", required=True, choices=sorted(RESULT_STATUSES))

    list_cmd = subparsers.add_parser("list-tasks", help="List task files.")
    list_cmd.add_argument("--owner", choices=sorted(OWNERS))
    list_cmd.add_argument("--status", choices=sorted(TASK_STATUSES))

    archive_cmd = subparsers.add_parser("archive-task", help="Archive a task and its result.")
    archive_cmd.add_argument("--task-id", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "create-task":
            path = create_task(args.owner, args.title)
            print(path)
        elif args.command == "set-task-status":
            path = update_task_status(args.task_id, args.status)
            print(path)
        elif args.command == "create-result":
            path = create_result(args.task_id, args.status)
            print(path)
        elif args.command == "list-tasks":
            for path in list_tasks(args.owner, args.status):
                print(path)
        elif args.command == "archive-task":
            archived_task, archived_result = archive_task(args.task_id)
            print(archived_task)
            if archived_result is not None:
                print(archived_result)
    except Exception as exc:
        print(f"error: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
