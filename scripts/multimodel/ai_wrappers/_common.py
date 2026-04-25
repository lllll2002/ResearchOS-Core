from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_PATH = Path(__file__).resolve().parent / "multimodel_config.json"
WORKFLOW_ROOT = Path(os.environ.get("RESEARCH_OS_WORKFLOW", PROJECT_ROOT / "workspace" / "current_task"))
EVENTS_ROOT = Path(os.environ.get("RESEARCH_OS_EVENTS", PROJECT_ROOT / "workspace" / "events"))
REQUEST_PATH = WORKFLOW_ROOT / "00_request.md"
PLAN_PATH = WORKFLOW_ROOT / "10_plan.md"
IMPLEMENTATION_PATH = WORKFLOW_ROOT / "30_implementation.md"


def wrapper_event_path(model: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return EVENTS_ROOT / f"wrapper-{model}-{stamp}.jsonl"


def append_wrapper_event(event_file: Path, event_type: str, payload: dict) -> None:
    event_file.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": datetime.now().isoformat(timespec="seconds"), "type": event_type, **payload}
    with event_file.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def get_env(name: str) -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value)
    except Exception:
        return ""


def read_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def default_reasoning_prompt() -> str:
    request = read_if_exists(REQUEST_PATH)
    plan = read_if_exists(PLAN_PATH)
    parts = []
    if request:
        parts.append("# Request\n" + request)
    if plan:
        parts.append("# Plan\n" + plan)
    if not parts:
        raise ValueError("No current_task context found. Provide --prompt or create 00_request.md / 10_plan.md first.")
    return "\n\n".join(parts)


def build_round_header(round_num: int, speaker: str, reasoning: str, prior_artifacts: str) -> str:
    """Return a team-mode round header string for prepending to an artifact.

    Format matches round-protocol.md:
        # [Round N] <speaker> — <YYYY-MM-DD>
        Router reasoning: <reasoning>
        Prior artifact(s) read: <prior_artifacts>
    """
    date = datetime.now().strftime("%Y-%m-%d")
    return (
        f"# [Round {round_num}] {speaker} — {date}\n"
        f"Router reasoning: {reasoning}\n"
        f"Prior artifact(s) read: {prior_artifacts}\n"
    )


def extract_usage_openai(body: dict) -> dict:
    """Extract usage fields from an OpenAI-compatible API response body."""
    u = body.get("usage") or {}
    tin = u.get("prompt_tokens")
    tout = u.get("completion_tokens")
    total = u.get("total_tokens")
    return {
        "tokens_in": tin,
        "tokens_out": tout,
        "total_tokens": total,
        "cost_usd": None,
        "usage_source": "api" if u else None,
    }


def extract_usage_ollama(body: dict) -> dict:
    """Extract usage fields from an Ollama /api/generate response body."""
    tin = body.get("prompt_eval_count")
    tout = body.get("eval_count")
    total = (tin or 0) + (tout or 0) if (tin is not None or tout is not None) else None
    return {
        "tokens_in": tin,
        "tokens_out": tout,
        "total_tokens": total,
        "cost_usd": None,
        "usage_source": "ollama" if (tin is not None or tout is not None) else None,
    }


def default_review_prompt() -> str:
    request = read_if_exists(REQUEST_PATH)
    plan = read_if_exists(PLAN_PATH)
    implementation = read_if_exists(IMPLEMENTATION_PATH)
    parts = []
    if request:
        parts.append("# Request\n" + request)
    if plan:
        parts.append("# Plan\n" + plan)
    if implementation:
        parts.append("# Implementation\n" + implementation)
    if not parts:
        raise ValueError("No current_task context found. Provide --prompt or create workflow artifacts first.")
    return "\n\n".join(parts)
