from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ai_wrappers._common import get_env


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_ROOT = Path(os.environ.get("RESEARCH_OS_VAULT", PROJECT_ROOT / "vault"))
CONFIG_PATH = PROJECT_ROOT / "scripts" / "ai_wrappers" / "multimodel_config.json"
CURRENT_TASK_DIR = PROJECT_ROOT / "workspace" / "current_task"


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def exists_status(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
    }


def port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_env(stage_name: str, stage: dict[str, Any]) -> dict[str, Any]:
    env_name = stage.get("api_key_env")
    if not env_name:
        return {"stage": stage_name, "kind": "env", "ok": True, "detail": "no api key required"}
    value = get_env(str(env_name))
    return {
        "stage": stage_name,
        "kind": "env",
        "ok": bool(value),
        "detail": f"{env_name} is set" if value else f"{env_name} is missing",
    }


def check_ollama(stage_name: str, stage: dict[str, Any]) -> dict[str, Any]:
    import urllib.request as _ur

    api_base = str(stage.get("api_base", ""))
    parsed = urlparse(api_base)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 11434

    # First confirm TCP port is open (catches service-down case fast).
    if not port_open(host, port):
        return {"stage": stage_name, "kind": "local_service", "ok": False, "detail": f"{host}:{port} not reachable"}

    # Then verify the HTTP API responds — bypass system proxy so VPN/proxy 502s don't give false positives.
    version_url = f"http://{host}:{port}/api/version"
    opener = _ur.build_opener(_ur.ProxyHandler({}))
    try:
        with opener.open(version_url, timeout=3) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            ver = body.get("version", "?")
        return {"stage": stage_name, "kind": "local_service", "ok": True, "detail": f"{host}:{port} reachable (ollama {ver})"}
    except Exception as exc:
        return {"stage": stage_name, "kind": "local_service", "ok": False, "detail": f"{host}:{port} port open but API failed: {exc}"}


def check_codex(stage_name: str, stage: dict[str, Any]) -> list[dict[str, Any]]:
    runner = Path(str(stage.get("runner", "")))
    codex_cmd = shutil.which("codex.cmd") or shutil.which("codex")
    return [
        {
            "stage": stage_name,
            "kind": "runner",
            "ok": runner.exists(),
            "detail": f"runner found: {runner}" if runner.exists() else f"runner missing: {runner}",
        },
        {
            "stage": stage_name,
            "kind": "cli",
            "ok": bool(codex_cmd),
            "detail": f"codex cli found: {codex_cmd}" if codex_cmd else "codex cli not found in PATH",
        },
    ]


_TASK_SENTINEL = "Describe the request here."


def _task_state() -> str:
    """Mirror of init_current_task.classify_current_task() — kept local to avoid import coupling."""
    summary = CURRENT_TASK_DIR / "50_summary.md"
    request = CURRENT_TASK_DIR / "00_request.md"
    if not summary.exists() or not request.exists():
        return "empty"
    if "status: done" in summary.read_text(encoding="utf-8"):
        return "completed"
    if _TASK_SENTINEL in request.read_text(encoding="utf-8"):
        return "fresh"
    return "in_progress"


def check_current_task() -> list[dict[str, Any]]:
    state = _task_state()

    # Map state to ok/warn/detail for the caller.
    # empty / fresh  → ready for a new task (OK)
    # in_progress    → task is running or context is live (WARN — not a blocker if intentional)
    # completed      → previous task done but not archived (WARN — start fresh)
    state_ok = state in ("empty", "fresh")
    state_detail = {
        "empty":       "uninitialized — run init_current_task.py before starting",
        "fresh":       "initialized and clean — ready for new task",
        "in_progress": "STALE: task in progress (00_request.md has content, 50_summary.md pending) — archive or use --force",
        "completed":   "STALE: previous task completed but not archived — run archive_current_task.py",
    }[state]

    results: list[dict[str, Any]] = [
        {
            "stage": "current_task",
            "kind": "state",
            "ok": state_ok,
            "detail": state_detail,
        }
    ]

    # Report missing artifacts only when the task is active — for empty/fresh states,
    # missing files are expected and init_current_task.py will create them.
    if state in ("in_progress", "completed"):
        required = ["00_request.md", "10_plan.md", "20_reasoning.md", "30_implementation.md",
                    "40_review.md", "50_summary.md", "task_board.md"]
        for name in required:
            path = CURRENT_TASK_DIR / name
            if not path.exists():
                results.append({
                    "stage": "current_task",
                    "kind": "artifact",
                    "ok": False,
                    "detail": f"missing: {name}",
                })

    return results


def run_checks() -> dict[str, Any]:
    config = load_config()
    checks: list[dict[str, Any]] = [
        {
            "stage": "config",
            "kind": "file",
            "ok": CONFIG_PATH.exists(),
            "detail": f"config found: {CONFIG_PATH}" if CONFIG_PATH.exists() else f"config missing: {CONFIG_PATH}",
        }
    ]

    for stage_name, stage in config.items():
        if not stage.get("enabled", True):
            checks.append(
                {
                    "stage": stage_name,
                    "kind": "enabled",
                    "ok": True,
                    "detail": "disabled by config",
                }
            )
            continue

        provider = stage.get("provider")
        if provider in {"deepseek", "glm"}:
            checks.append(check_env(stage_name, stage))
        elif provider == "ollama":
            checks.append(check_ollama(stage_name, stage))
        elif provider == "openai-codex-bridge":
            checks.extend(check_codex(stage_name, stage))

    checks.extend(check_current_task())

    ok = all(item["ok"] for item in checks)
    return {"ok": ok, "config": exists_status(CONFIG_PATH), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check multimodel workflow readiness.")
    parser.add_argument("--json", action="store_true", help="Output JSON only.")
    args = parser.parse_args()

    report = run_checks()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1

    print(f"overall: {'OK' if report['ok'] else 'NOT READY'}")
    for item in report["checks"]:
        mark = "OK" if item["ok"] else "FAIL"
        print(f"[{mark}] {item['stage']} / {item['kind']} - {item['detail']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
