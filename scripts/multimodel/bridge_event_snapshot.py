from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_ROOT = Path(os.environ.get("RESEARCH_OS_VAULT", PROJECT_ROOT / "vault"))
BRIDGE_ROOT = VAULT_ROOT / ".ai-bridge"
EVENTS_ROOT = PROJECT_ROOT / "workspace" / "events"
RESULTS_ROOT = BRIDGE_ROOT / "results"
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
OUTPUT_JS = WORKSPACE_ROOT / "bridge-live-data.js"


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


def load_result(task_id: str) -> dict[str, Any] | None:
    path = RESULTS_ROOT / f"{task_id}-result.md"
    if not path.exists():
        return None
    fm, body = parse_frontmatter(read_text(path))
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    return {
        "path": str(path),
        "status": fm.get("status"),
        "summary": lines[:8],
    }


def load_wrapper_event_file(path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Handle event files produced by qwen_reason / deepseek_reason / glm_review wrappers."""
    started = next((r for r in records if r.get("type") == "stage.started"), {})
    model = started.get("model", "unknown")
    config_model = started.get("config_model", "")

    timeline: list[dict[str, str]] = []
    stage = "queued"
    latest_status = "pending"
    output_path: str | None = None

    for record in records:
        event_type = record.get("type", "")
        if event_type == "stage.started":
            output_path = record.get("output_path")
            label = f"{config_model or model}"
            timeline.append({"speaker": "Runner", "text": f"[{model}] Stage started — model: {label}"})
            stage = "running"
            latest_status = "in_progress"
        elif event_type == "stage.provider_called":
            api_base = record.get("api_base", "")
            timeline.append({"speaker": model, "text": f"Calling {api_base}"})
        elif event_type == "output.written":
            output_path = record.get("output_path", output_path)
            timeline.append({"speaker": model, "text": f"Output written → {output_path}"})
        elif event_type == "stage.completed":
            timeline.append({"speaker": "Runner", "text": f"[{model}] Stage completed."})
            stage = "done"
            latest_status = "done"
        elif event_type == "stage.failed":
            error = record.get("error", "")
            timeline.append({"speaker": "Runner", "text": f"[{model}] Stage failed: {error}"})
            stage = "blocked"
            latest_status = "blocked"

    result = {"status": latest_status, "summary": [f"output: {output_path}"], "path": None} if output_path else None

    return {
        "task_id": path.stem,  # e.g. wrapper-qwen-20260403-120000 — unique, no collision
        "task_path": None,
        "scope": f"wrapper:{model}",
        "status": latest_status,
        "stage": stage,
        "updated": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "event_path": str(path),
        "task_card": None,
        "timeline": timeline[-20:],
        "stdout_preview": [],
        "stderr_preview": [],
        "debug_note": "Wrapper stage event — output written directly to stage file.",
        "result": result,
    }


def load_event_file(path: Path) -> dict[str, Any]:
    records = [json.loads(line) for line in read_text(path).splitlines() if line.strip()]
    task_snapshot = next((item for item in records if item.get("type") == "task.snapshot"), {})

    # Wrapper event files have no task.snapshot and are named wrapper-{model}-{stamp}.jsonl
    if not task_snapshot and path.stem.startswith("wrapper-"):
        return load_wrapper_event_file(path, records)

    task_id = task_snapshot.get("task_id") or path.stem
    result = load_result(task_id)

    timeline: list[dict[str, str]] = []
    stage = "queued"
    latest_status = task_snapshot.get("status") or "pending"
    stdout_preview: list[str] = []
    stderr_preview: list[str] = []
    for record in records:
        event_type = record.get("type", "event")
        if event_type == "task.status":
            latest_status = str(record.get("status") or latest_status)
            stage = latest_status
        elif event_type == "runner.received":
            timeline.append({"speaker": "Claude", "text": f"Created bridge task {task_id}."})
        elif event_type == "runner.dry_run":
            timeline.append({"speaker": "Runner", "text": "Dry-run validation passed."})
            stage = "validated"
        elif event_type == "codex.started":
            timeline.append({"speaker": "Runner", "text": "Codex execution started."})
            stage = "running"
        elif event_type == "formal.output.validated":
            timeline.append({"speaker": "Runner", "text": "UTF-8 formal outputs validated."})
        elif event_type == "codex.debug.stdout":
            line = str(record.get("line") or "")
            if line:
                stdout_preview.append(line)
        elif event_type == "codex.debug.stderr":
            line = str(record.get("line") or "")
            if line:
                stderr_preview.append(line)
        elif event_type == "runner.completed":
            timeline.append({"speaker": "Runner", "text": "Runner completed successfully."})
            stage = "done"
            latest_status = "done"
        elif event_type == "runner.failed":
            timeline.append({"speaker": "Runner", "text": "Runner failed."})
            stage = "blocked"
            latest_status = "blocked"
        elif event_type == "runner.error":
            timeline.append({"speaker": "Runner", "text": str(record.get("message") or "Unexpected runner error")})
            stage = "blocked"
            latest_status = "blocked"

    if result and result.get("status") == "done":
        stage = "done"
        latest_status = "done"
        timeline.append({"speaker": "Claude", "text": "Result card is available."})

    return {
        "task_id": task_id,
        "task_path": task_snapshot.get("task_path"),
        "scope": task_snapshot.get("scope"),
        "status": latest_status,
        "stage": stage,
        "updated": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "event_path": str(path),
        "task_card": task_snapshot.get("task_card"),
        "timeline": timeline[-20:],
        "stdout_preview": stdout_preview[-12:],
        "stderr_preview": stderr_preview[-12:],
        "debug_note": "Console previews are debug-only and must not be copied into formal documents.",
        "result": result,
    }


# ---------------------------------------------------------------------------
# v2 helpers — additive only, v1 items[] is untouched
# ---------------------------------------------------------------------------

_PROVIDER_MAP: dict[str, str] = {
    "qwen": "ollama",
    "deepseek": "deepseek-api",
    "glm": "glm-api",
    "codex": "codex",
    "claude": "claude",
}


def classify_run_type(path: Path) -> str:
    stem = path.stem
    if stem.startswith("wrapper-"):
        return "wrapper"
    if stem.startswith("team-"):
        return "team"
    if stem.startswith("TASK-"):
        return "bridge"
    return "unknown"


def _check_round_header(artifact_path: str) -> bool | None:
    """Return True/False if file exists; None if file is missing (archived/moved)."""
    p = Path(artifact_path)
    if not p.exists():
        return None
    try:
        first_line = p.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
        return first_line.startswith("# [Round ")
    except OSError:
        return None


_EXCERPT_MAX_LINES = 8
_EXCERPT_MAX_CHARS = 400

# Required headers for a valid review verdict block — must ALL be present or verdict is None.
_VERDICT_VALUES = frozenset({"pass", "revise", "reject"})


def _read_artifact_text(p: Path) -> str | None:
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _artifact_excerpt(text: str) -> str | None:
    """Return first N non-blank lines, capped at _EXCERPT_MAX_CHARS. Returns None if empty."""
    lines = [ln for ln in text.splitlines() if ln.strip()][:_EXCERPT_MAX_LINES]
    if not lines:
        return None
    excerpt = "\n".join(lines)
    if len(excerpt) > _EXCERPT_MAX_CHARS:
        excerpt = excerpt[:_EXCERPT_MAX_CHARS].rstrip() + "…"
    return excerpt


def _parse_sections(text: str) -> dict[str, list[str]]:
    """Split text into {## Header: [content lines]} dict. Strict: only ## level headers."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = buf
            current = line.strip()
            buf = []
        elif current is not None and line.strip():
            buf.append(line.strip())
    if current is not None:
        sections[current] = buf
    return sections


def _parse_review_verdict(text: str) -> dict[str, Any] | None:
    """
    Strictly parse GLM review verdict from artifact text.
    Returns None unless '## Verdict' is present and its first content line is
    exactly one of: pass, revise, reject (case-insensitive).
    No guessing — any ambiguity returns None.
    """
    if "## Verdict" not in text:
        return None
    sections = _parse_sections(text)
    verdict_lines = sections.get("## Verdict", [])
    if not verdict_lines:
        return None
    verdict_value = verdict_lines[0].lower().strip("*_ ")
    if verdict_value not in _VERDICT_VALUES:
        return None
    blocking = [
        ln.lstrip("- *").strip()
        for ln in sections.get("## Blocking Issues", [])
        if ln.lstrip("- *").strip() and ln.lstrip("- *").strip().lower() != "none"
    ]
    non_blocking = [
        ln.lstrip("- *").strip()
        for ln in sections.get("## Non-Blocking Issues", [])
        if ln.lstrip("- *").strip() and ln.lstrip("- *").strip().lower() != "none"
    ]
    rec_lines = sections.get("## Recommendation", [])
    return {
        "verdict": verdict_value,
        "blocking": blocking,
        "non_blocking": non_blocking,
        "recommendation": rec_lines[0].lstrip("- *").strip() if rec_lines else None,
    }


def _parse_synthesis_claims(text: str) -> dict[str, Any] | None:
    """
    Strictly parse accepted/rejected/uncertain claims from a synthesis artifact.
    Returns None unless BOTH '## Accepted' and '## Rejected' are present.
    """
    if "## Accepted" not in text or "## Rejected" not in text:
        return None
    sections = _parse_sections(text)
    def extract(key: str) -> list[str]:
        return [
            ln.lstrip("- *").strip()
            for ln in sections.get(key, [])
            if ln.lstrip("- *").strip()
        ]
    return {
        "accepted": extract("## Accepted"),
        "rejected": extract("## Rejected"),
        "uncertain": extract("## Uncertain"),
    }


def _artifact_entry(artifact_path: str, written_at: str) -> dict[str, Any]:
    p = Path(artifact_path)
    size = p.stat().st_size if p.exists() else 0
    text = _read_artifact_text(p)
    return {
        "path": artifact_path,
        "stage_file": p.name,
        "size_bytes": size,
        "written_at": written_at,
        "has_round_header": _check_round_header(artifact_path),
        "excerpt": _artifact_excerpt(text) if text is not None else None,
        "review_verdict": _parse_review_verdict(text) if text is not None else None,
    }


def _ts_delta_ms(ts_start: str, ts_end: str) -> int | None:
    try:
        a = datetime.fromisoformat(ts_start)
        b = datetime.fromisoformat(ts_end)
        return max(0, int((b - a).total_seconds() * 1000))
    except Exception:
        return None


def _build_v2_run_bridge(path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    task_snapshot = next((r for r in records if r.get("type") == "task.snapshot"), {})
    task_id = task_snapshot.get("task_id") or path.stem
    raw_card = task_snapshot.get("task_card") or ""
    if isinstance(raw_card, dict):
        task_card: dict[str, Any] = raw_card
    elif isinstance(raw_card, str) and raw_card.strip():
        task_card, _ = parse_frontmatter(raw_card)
    else:
        task_card = {}
    title = str(task_card.get("title") or task_card.get("id") or task_id)

    status = "pending"
    started_at: str | None = None
    completed_at: str | None = None
    blocker_reason: str | None = None
    codex_start_ts: str | None = None
    codex_end_ts: str | None = None

    for r in records:
        t = r.get("type", "")
        ts = r.get("ts", "")
        if t == "runner.received" and not started_at:
            started_at = ts
        elif t == "codex.started":
            codex_start_ts = ts
            status = "in_progress"
        elif t == "codex.completed":
            codex_end_ts = ts
        elif t == "task.status":
            status = str(r.get("status") or status)
        elif t == "runner.completed":
            status = "done"
            completed_at = ts
        elif t in ("runner.failed", "runner.error"):
            status = "blocked"
            completed_at = ts
            blocker_reason = str(r.get("message") or r.get("error") or "Runner failed")

    stages: list[dict[str, Any]] = []
    if codex_start_ts:
        end_ts = codex_end_ts or completed_at
        stages.append({
            "name": "codex",
            "provider": "codex",
            "model": "codex",
            "status": "completed" if status == "done" else ("failed" if status == "blocked" else "running"),
            "started_at": codex_start_ts,
            "completed_at": end_ts,
            "duration_ms": _ts_delta_ms(codex_start_ts, end_ts) if end_ts else None,
            "tokens_in": None,
            "tokens_out": None,
            "cost_usd": None,
            "artifact_path": None,
        })

    result = load_result(task_id)
    artifacts: list[dict[str, Any]] = []
    if result and result.get("path"):
        artifacts.append(_artifact_entry(result["path"], completed_at or ""))

    return {
        "id": path.stem,
        "run_type": "bridge",
        "task_id": task_id,
        "title": title,
        "status": status,
        "started_at": started_at,
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "completed_at": completed_at,
        "event_file": str(path),
        "task_card": task_card,
        "stages": stages,
        "artifacts": artifacts,
        "blocker_reason": blocker_reason,
    }


def _build_v2_run_wrapper(path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    started_ev = next((r for r in records if r.get("type") == "stage.started"), {})
    completed_ev = next((r for r in records if r.get("type") == "stage.completed"), None)
    failed_ev = next((r for r in records if r.get("type") == "stage.failed"), None)
    output_ev = next((r for r in records if r.get("type") == "output.written"), None)

    model_key = str(started_ev.get("model") or "unknown")
    config_model = str(started_ev.get("config_model") or model_key)
    provider = _PROVIDER_MAP.get(model_key, "unknown")

    started_at = started_ev.get("ts")
    end_ev = completed_ev or failed_ev
    completed_at = end_ev.get("ts") if end_ev else None
    status = "done" if completed_ev else ("blocked" if failed_ev else "in_progress")
    stage_status = "completed" if completed_ev else ("failed" if failed_ev else "running")
    blocker_reason = str(failed_ev.get("error") or "Stage failed") if failed_ev else None
    artifact_path = str((output_ev.get("output_path") if output_ev else None) or started_ev.get("output_path") or "")

    stage: dict[str, Any] = {
        "name": model_key,
        "provider": provider,
        "model": config_model,
        "status": stage_status,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": _ts_delta_ms(started_at, completed_at) if started_at and completed_at else None,
        "tokens_in": completed_ev.get("tokens_in") if completed_ev else None,
        "tokens_out": completed_ev.get("tokens_out") if completed_ev else None,
        "total_tokens": completed_ev.get("total_tokens") if completed_ev else None,
        "cost_usd": completed_ev.get("cost_usd") if completed_ev else None,
        "usage_source": completed_ev.get("usage_source") if completed_ev else None,
        "artifact_path": artifact_path or None,
    }

    artifacts: list[dict[str, Any]] = []
    if artifact_path:
        written_at = output_ev.get("ts", "") if output_ev else ""
        artifacts.append(_artifact_entry(artifact_path, written_at))

    parts = path.stem.split("-")
    model_part = parts[1] if len(parts) > 1 else model_key
    date_part = parts[2] if len(parts) > 2 else ""
    if len(date_part) == 8 and date_part.isdigit():
        date_fmt = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
    else:
        date_fmt = date_part
    title = f"{model_part} · {date_fmt}"

    return {
        "id": path.stem,
        "run_type": "wrapper",
        "task_id": None,
        "title": title,
        "status": status,
        "started_at": started_at,
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "completed_at": completed_at,
        "event_file": str(path),
        "task_card": {},
        "stages": [stage],
        "artifacts": artifacts,
        "blocker_reason": blocker_reason,
    }


def _build_v2_run_team(path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    started_ev = next((r for r in records if r.get("type") == "team.started"), {})
    stopped_ev = next((r for r in records if r.get("type") == "team.stopped"), None)

    started_at = started_ev.get("ts")
    status = "in_progress"
    completed_at: str | None = None
    blocker_reason: str | None = None

    if stopped_ev:
        completed_at = stopped_ev.get("ts")
        reason = str(stopped_ev.get("reason") or "")
        status = "blocked" if reason == "glm_block" else "done"
        if reason == "glm_block":
            blocker_reason = "GLM issued BLOCK verdict"

    assigned: dict[int, dict] = {r["round"]: r for r in records if r.get("type") == "team.round.assigned" and "round" in r}
    completed_rounds: dict[int, dict] = {r["round"]: r for r in records if r.get("type") == "team.round.completed" and "round" in r}
    failed_rounds: dict[int, dict] = {r["round"]: r for r in records if r.get("type") == "team.round.failed" and "round" in r}

    stages: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []

    for round_num in sorted(set(assigned) | set(completed_rounds) | set(failed_rounds)):
        a = assigned.get(round_num, {})
        c = completed_rounds.get(round_num, {})
        f = failed_rounds.get(round_num, {})
        speaker = str(a.get("speaker") or "unknown")
        provider = _PROVIDER_MAP.get(speaker, "unknown")
        round_status = "completed" if c else ("failed" if f else "running")
        artifact_path = str(c.get("artifact_path") or "")
        end_ts = c.get("ts") or f.get("ts")
        # Infer prior artifacts: previous round's artifact (if any)
        prior_artifacts = str(stages[-1]["artifact_path"]) if stages and stages[-1].get("artifact_path") else ""

        stages.append({
            "name": f"round{round_num}:{speaker}",
            "provider": provider,
            "model": speaker,
            "status": round_status,
            "started_at": a.get("ts"),
            "completed_at": end_ts,
            "duration_ms": _ts_delta_ms(a.get("ts", ""), end_ts) if a.get("ts") and end_ts else None,
            "tokens_in": None,
            "tokens_out": None,
            "cost_usd": None,
            "artifact_path": artifact_path or None,
            "router_reasoning": str(a.get("router_reasoning") or ""),
            "prior_artifacts": prior_artifacts,
        })
        if artifact_path:
            artifacts.append(_artifact_entry(artifact_path, c.get("ts", "")))

    stop_reason = str(stopped_ev.get("reason") or "") if stopped_ev else None

    synthesis_ev = next((r for r in records if r.get("type") == "team.synthesis.completed"), None)
    synthesis: dict[str, Any] | None = None
    if synthesis_ev:
        synth_path = str(synthesis_ev.get("artifact") or "")
        synth_file = Path(synth_path).name if synth_path else None
        synth_excerpt: str | None = None
        synth_structured: dict[str, Any] | None = None
        if synth_path:
            synth_text = _read_artifact_text(Path(synth_path))
            if synth_text:
                synth_excerpt = _artifact_excerpt(synth_text)
                synth_structured = _parse_synthesis_claims(synth_text)
            artifacts.append(_artifact_entry(synth_path, synthesis_ev.get("ts", "")))
        synthesis = {
            "synthesizer": str(synthesis_ev.get("synthesizer") or ""),
            "artifact_path": synth_path or None,
            "artifact_file": synth_file,
            "excerpt": synth_excerpt,
            "structured": synth_structured,
        }

    stem = path.stem[5:] if path.stem.startswith("team-") else path.stem
    parts = stem.rsplit("-", 2)
    title = parts[0] if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit() else stem

    return {
        "id": path.stem,
        "run_type": "team",
        "task_id": None,
        "title": title,
        "status": status,
        "started_at": started_at,
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "completed_at": completed_at,
        "event_file": str(path),
        "task_card": {},
        "stages": stages,
        "artifacts": artifacts,
        "blocker_reason": blocker_reason,
        "stop_reason": stop_reason,
        "synthesis": synthesis,
    }


def build_v2_run(path: Path) -> dict[str, Any] | None:
    try:
        records = [json.loads(line) for line in read_text(path).splitlines() if line.strip()]
    except Exception:
        return None
    run_type = classify_run_type(path)
    if run_type == "bridge":
        return _build_v2_run_bridge(path, records)
    if run_type == "wrapper":
        return _build_v2_run_wrapper(path, records)
    if run_type == "team":
        return _build_v2_run_team(path, records)
    return None


def build_v2_runs(limit: int) -> list[dict[str, Any]]:
    event_files = sorted(EVENTS_ROOT.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    runs = []
    for path in event_files[:limit]:
        run = build_v2_run(path)
        if run is not None:
            runs.append(run)
    return runs


def _run_file_status(records: list[dict[str, Any]]) -> str:
    types = {r.get("type") for r in records}
    if "stage.completed" in types or "runner.completed" in types:
        return "done"
    if "stage.failed" in types or "runner.failed" in types or "runner.error" in types:
        return "blocked"
    return "in_progress"


def build_v2_pipelines(limit: int) -> list[dict[str, Any]]:
    session_files = sorted(
        EVENTS_ROOT.glob("session-coo-*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]
    if not session_files:
        return []

    # Pre-load all non-session event files once for efficiency
    candidate_files: list[tuple[Path, list[dict[str, Any]]]] = []
    for path in EVENTS_ROOT.glob("*.jsonl"):
        if path.name.startswith("session-"):
            continue
        try:
            records = [json.loads(line) for line in read_text(path).splitlines() if line.strip()]
            candidate_files.append((path, records))
        except Exception:
            continue

    pipelines: list[dict[str, Any]] = []
    for sf in session_files:
        try:
            records = [json.loads(line) for line in read_text(sf).splitlines() if line.strip()]
        except Exception:
            continue
        started = next((r for r in records if r.get("type") == "pipeline.started"), None)
        if not started:
            continue
        session_id = str(started.get("session_id") or "")
        if not session_id:
            continue

        child_runs: list[dict[str, Any]] = []
        for path, ev_records in candidate_files:
            if not any(r.get("session_id") == session_id for r in ev_records):
                continue
            run_type = classify_run_type(path)
            first_ts = next((r.get("ts", "") for r in ev_records), "")
            child_runs.append({
                "id": path.stem,
                "run_type": run_type,
                "ts": first_ts,
                "status": _run_file_status(ev_records),
            })
        child_runs.sort(key=lambda r: r.get("ts") or "")

        statuses = {r["status"] for r in child_runs}
        if "blocked" in statuses:
            pipeline_status = "blocked"
        elif statuses and statuses <= {"done"}:
            pipeline_status = "done"
        else:
            pipeline_status = "in_progress"

        pipelines.append({
            "session_id": session_id,
            "route": str(started.get("route") or "unknown"),
            "title": str(started.get("title") or session_id),
            "status": pipeline_status,
            "started_at": str(started.get("ts") or ""),
            "updated_at": datetime.fromtimestamp(sf.stat().st_mtime).isoformat(timespec="seconds"),
            "child_runs": child_runs,
        })

    return pipelines


# ---------------------------------------------------------------------------
# end v2 helpers
# ---------------------------------------------------------------------------


def build_snapshot(limit: int) -> dict[str, Any]:
    event_files = sorted(EVENTS_ROOT.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    items = [load_event_file(path) for path in event_files[:limit]]
    counts = {
        "queued": sum(1 for item in items if item["stage"] in {"queued", "validated"}),
        "running": sum(1 for item in items if item["stage"] == "running"),
        "done": sum(1 for item in items if item["stage"] == "done"),
        "blocked": sum(1 for item in items if item["stage"] == "blocked"),
    }
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "counts": counts,
        "items": items,
        "v2_runs": build_v2_runs(limit),
        "v2_pipelines": build_v2_pipelines(limit),
    }


def write_snapshot(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "window.BRIDGE_LIVE_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
    path.write_text(payload, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate bridge live data JS from event files.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output", default=str(OUTPUT_JS))
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    output = Path(args.output)
    while True:
        write_snapshot(output, build_snapshot(args.limit))
        print(output)
        if not args.watch:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
