from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue

import ai_bridge


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_ROOT = PROJECT_ROOT / "workspace" / "codex-temp"
EVENTS_ROOT = PROJECT_ROOT / "workspace" / "events"
REQUIRED_KEYS = {
    "id",
    "owner",
    "status",
    "inputs",
    "allowed_write_paths",
    "expected_output",
    "rollback",
}
UTF8_ENV_OVERRIDES = {
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
}


class BridgeRunnerError(Exception):
    pass


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise BridgeRunnerError("Task file is missing frontmatter.")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise BridgeRunnerError("Task file frontmatter is not closed.")
    block = text[4:end]
    data: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def validate_task(path: Path, data: dict[str, str]) -> str:
    missing = sorted(key for key in REQUIRED_KEYS if key not in data)
    if missing:
        raise BridgeRunnerError(f"Task is missing required keys: {', '.join(missing)}")
    task_id = data["id"]
    if data["owner"] != "codex":
        raise BridgeRunnerError(f"{task_id} owner must be codex.")
    if data["status"] != "pending":
        raise BridgeRunnerError(f"{task_id} status must be pending.")
    if path.parent != ai_bridge.TASKS_DIR:
        raise BridgeRunnerError(f"Task must live under {ai_bridge.TASKS_DIR}")
    return task_id


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def log_path(task_id: str) -> Path:
    return LOG_ROOT / f"{task_id}-{stamp()}.log"


def event_path(task_id: str) -> Path:
    return EVENTS_ROOT / f"{task_id}-{stamp()}.jsonl"


def write_log(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def append_event(path: Path, event_type: str, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": now_iso(),
        "type": event_type,
        **payload,
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_codex_message(task_path: Path) -> str:
    task_content = task_path.read_text(encoding="utf-8")
    return (
        "Process this bridge task exactly. The full task card is below.\n\n"
        f"Task file path: {task_path}\n\n"
        f"Task card content:\n```\n{task_content}\n```\n\n"
        "Requirements:\n"
        "- Obey allowed_write_paths strictly and do not write outside those paths.\n"
        "- Create or update the matching result card under the ai-bridge results directory.\n"
        "- Set the task status field to done on success or blocked on failure.\n"
        "- Formal deliverables must be written directly to UTF-8 files.\n"
        "- Treat stdout/stderr and terminal transcripts as debug-only, never as the source for formal documents.\n"
        "- If you need Chinese output in a formal artifact, write the file directly in UTF-8 instead of copying console text.\n"
        "- Keep the final response concise."
    )


def reader_worker(stream, stream_name: str, queue: Queue[tuple[str, str]]) -> None:
    try:
        for line in iter(stream.readline, ""):
            queue.put((stream_name, line.rstrip("\n")))
    finally:
        stream.close()


def build_debug_log(cmd: list[str], return_code: int, stdout_lines: list[str], stderr_lines: list[str]) -> str:
    output = [
        "UTF-8 bridge debug log",
        "Formal source of truth: UTF-8 files under .ai-bridge and allowed_write_paths",
        "Console output below is debug-only and must not be copied back into formal documents.",
        "",
        f"command: {' '.join(cmd)}",
        f"returncode: {return_code}",
        "",
        "stdout (debug only):",
        *stdout_lines,
        "",
        "stderr (debug only):",
        *stderr_lines,
    ]
    return "\n".join(output)


def validate_formal_outputs(task_id: str) -> Path:
    # Task status is managed by the runner, not by Codex.
    # Codex cannot write the task card (it is not in allowed_write_paths).
    # The runner sets status to "done" before calling this function on success.
    result_file = ai_bridge.result_path(task_id)
    if not result_file.exists():
        raise BridgeRunnerError(f"Result file not found: {result_file}")
    result_text = result_file.read_text(encoding="utf-8-sig")
    if not result_text.strip():
        raise BridgeRunnerError(f"Result file is empty: {result_file}")
    result_data = parse_frontmatter(result_text)
    if result_data.get("status") not in {"done", "partial", "failed"}:
        raise BridgeRunnerError(f"Result file status is invalid: {result_file}")
    return result_file


def run_codex(task_id: str, task_path: Path, log_file: Path, event_file: Path, codex_command: str | None) -> int:
    message = build_codex_message(task_path)
    cmd = [codex_command or "codex.cmd", "exec", "--skip-git-repo-check", "-s", "danger-full-access", "-"]
    append_event(event_file, "codex.started", {"task_id": task_id, "command": cmd, "task_path": str(task_path)})

    env = os.environ.copy()
    env.update(UTF8_ENV_OVERRIDES)
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(task_path.parent.parent.parent),
        env=env,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None
    proc.stdin.write(message)
    proc.stdin.close()

    queue: Queue[tuple[str, str]] = Queue()
    threads = [
        threading.Thread(target=reader_worker, args=(proc.stdout, "stdout", queue), daemon=True),
        threading.Thread(target=reader_worker, args=(proc.stderr, "stderr", queue), daemon=True),
    ]
    for thread in threads:
        thread.start()

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    while True:
        try:
            stream_name, line = queue.get(timeout=0.2)
            if stream_name == "stdout":
                stdout_lines.append(line)
            else:
                stderr_lines.append(line)
            if line.strip():
                append_event(event_file, f"codex.debug.{stream_name}", {"task_id": task_id, "line": line})
        except Empty:
            if proc.poll() is not None and queue.empty():
                break

    return_code = proc.wait()
    append_event(event_file, "codex.completed", {"task_id": task_id, "returncode": return_code})
    write_log(log_file, build_debug_log(cmd, return_code, stdout_lines, stderr_lines))
    return return_code


def trigger_snapshot() -> None:
    """Fire a one-shot snapshot refresh so the live dashboard stays current."""
    snapshot_script = Path(__file__).parent / "bridge_event_snapshot.py"
    if snapshot_script.exists():
        subprocess.Popen(
            [sys.executable, str(snapshot_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one Codex bridge task.")
    parser.add_argument("--task", required=True, help="Absolute path to a specific task card.")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not invoke Codex.")
    parser.add_argument("--codex-command", help="Executable used to invoke Codex. Defaults to `codex.cmd`.")
    parser.add_argument("--session-id", default=None, help="Pipeline session ID for grouping runs in Bridge Live v2.")
    parser.add_argument(
        "--result-status-on-error",
        default="blocked",
        choices=("blocked", "failed"),
        help="Task/result status used when Codex execution fails.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task_path = Path(args.task)
    if not task_path.exists():
        raise BridgeRunnerError(f"Task file not found: {task_path}")

    text = ai_bridge.read_text(task_path)
    data = parse_frontmatter(text)
    task_id = validate_task(task_path, data)

    if args.dry_run:
        print(f"validated: {task_path}")
        print(f"task_id: {task_id}")
        return 0

    log_file = log_path(task_id)
    event_file = event_path(task_id)

    sid = {"session_id": args.session_id} if args.session_id else {}
    append_event(event_file, "runner.received", {"task_id": task_id, "task_path": str(task_path), **sid})
    append_event(
        event_file,
        "task.snapshot",
        {
            "task_id": task_id,
            "task_path": str(task_path),
            "owner": data.get("owner"),
            "status": data.get("status"),
            "scope": data.get("scope"),
            "task_card": text,
        },
    )

    ai_bridge.update_task_status(task_id, "in_progress")
    append_event(event_file, "task.status", {"task_id": task_id, "status": "in_progress"})
    try:
        code = run_codex(task_id, task_path, log_file, event_file, args.codex_command)
        if code != 0:
            ai_bridge.update_task_status(task_id, "blocked")
            ai_bridge.create_result(task_id, "failed" if args.result_status_on_error == "failed" else "partial")
            append_event(event_file, "task.status", {"task_id": task_id, "status": "blocked"})
            append_event(event_file, "runner.failed", {"task_id": task_id, "log_path": str(log_file), "returncode": code})
            trigger_snapshot()
            print(f"blocked: {task_path}")
            print(f"log: {log_file}")
            print(f"events: {event_file}")
            return code

        ai_bridge.update_task_status(task_id, "done")
        append_event(event_file, "task.status", {"task_id": task_id, "status": "done"})
        result_file = validate_formal_outputs(task_id)
        append_event(event_file, "formal.output.validated", {"task_id": task_id, "result_path": str(result_file)})
        append_event(event_file, "runner.completed", {"task_id": task_id, "log_path": str(log_file), "returncode": code})
        trigger_snapshot()
        print(f"completed: {task_path}")
        print(f"result: {result_file}")
        print(f"log: {log_file}")
        print(f"events: {event_file}")
        return 0
    except Exception as exc:
        ai_bridge.update_task_status(task_id, "blocked")
        ai_bridge.create_result(task_id, "failed" if args.result_status_on_error == "failed" else "partial")
        append_event(event_file, "task.status", {"task_id": task_id, "status": "blocked"})
        append_event(event_file, "runner.error", {"task_id": task_id, "message": str(exc)})
        trigger_snapshot()
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BridgeRunnerError as exc:
        print(f"error: {exc}")
        raise SystemExit(1) from exc
