from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from _common import append_wrapper_event, get_env, get_model_config, wrapper_event_path


class TaskState:
    def __init__(self, session_dir: Path):
        self.state_file = session_dir / "task_state.json"
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            self.state = json.loads(self.state_file.read_text(encoding="utf-8"))
            return
        self.state = {
            "stages": {},
            "current_stage": None,
            "artifacts": {},
            "continuation_markers": {},
        }

    def save(self) -> None:
        self.state_file.write_text(json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8")

    def set_stage_status(self, stage_name: str, status: str, model: str) -> None:
        self.state["current_stage"] = stage_name
        self.state["stages"][stage_name] = {
            "status": status,
            "model": model,
            "timestamp": self._now(),
        }
        self.save()

    def register_artifact(self, artifact_name: str, path: Path, description: str) -> None:
        self.state["artifacts"][artifact_name] = {
            "path": str(path),
            "description": description,
            "created_at": self._now(),
        }
        self.save()

    def set_continuation_marker(self, marker: str, position: int) -> None:
        self.state["continuation_markers"][marker] = {
            "position": position,
            "timestamp": self._now(),
        }
        self.save()

    def _now(self) -> str:
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat()


class OutputManager:
    def __init__(self, write_path: Path, append_path: Path | None = None):
        self.write_path = write_path
        self.append_path = append_path
        self.write_path.parent.mkdir(parents=True, exist_ok=True)
        if self.append_path is not None:
            self.append_path.parent.mkdir(parents=True, exist_ok=True)

    def write_output(self, content: str, mode: str = "write", truncate_marker: str | None = None) -> tuple[bool, int]:
        target = self.append_path if mode == "append" and self.append_path else self.write_path
        existing = target.read_text(encoding="utf-8") if target.exists() else ""

        if mode == "append":
            final_content = existing + ("\n" if existing and not existing.endswith("\n") else "") + content
        elif mode == "continue":
            if existing:
                if truncate_marker and truncate_marker in existing:
                    before, _sep, _after = existing.rpartition(truncate_marker)
                    final_content = before + truncate_marker + "\n" + content
                else:
                    final_content = existing + ("\n" if not existing.endswith("\n") else "") + content
            else:
                final_content = content
        else:
            final_content = content

        target.write_text(final_content, encoding="utf-8", newline="\n")
        was_truncated = "[TRUNCATED]" in final_content or final_content.rstrip().endswith("...")
        return was_truncated, len(final_content.encode("utf-8"))


def read_file_content(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return path.read_text(encoding="utf-8")


def build_prompt(
    task: str,
    prompt: str,
    read_file: str | None = None,
    continue_from: str | None = None,
    existing_output: str | None = None,
) -> str:
    instructions = {
        "reason": "Produce a reasoning memo with assumptions, edge cases, recommended path, and rejected paths.",
        "write": "Write the requested content directly and completely.",
        "review": "Review the provided content and return specific, actionable feedback.",
        "execute": "Execute the task and return the direct result.",
        "continue": "Continue the existing content seamlessly from the stopping point.",
    }
    parts = [f"Task type: {task}", f"Primary instruction: {instructions.get(task, 'Complete the task.')}"]
    if read_file:
        parts.append(f"<INPUT_FILE path=\"{read_file}\">\n{read_file_content(read_file)}\n</INPUT_FILE>")
    if existing_output:
        parts.append(f"<EXISTING_OUTPUT>\n{existing_output}\n</EXISTING_OUTPUT>")
    if continue_from:
        parts.append(f"Continuation marker: {continue_from}")
    if prompt:
        parts.append(prompt)
    return "\n\n".join(parts)


def call_model(model_type: str, config: dict, prompt: str, max_tokens: int, session_id: str | None = None) -> tuple[str, bool, dict]:
    event_file = wrapper_event_path(model_type)
    sid = {"session_id": session_id} if session_id else {}
    append_wrapper_event(event_file, "stage.started", {"model": model_type, "config_model": config.get("model"), **sid})

    if model_type == "qwen":
        return _call_qwen(config, prompt, max_tokens, event_file, sid)
    if model_type == "deepseek":
        return _call_deepseek(config, prompt, max_tokens, event_file, sid)
    if model_type == "glm":
        return _call_glm(config, prompt, max_tokens, event_file, sid)
    if model_type == "claude":
        return _call_claude(config, prompt, max_tokens, event_file, sid)
    raise ValueError(f"Unknown model type: {model_type}")


def _call_qwen(config: dict, prompt: str, max_tokens: int, event_file: Path, session_id: dict) -> tuple[str, bool, dict]:
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {
            "temperature": float(config.get("temperature", 0.3)),
            "num_predict": max_tokens,
            "num_ctx": int(config.get("num_ctx", 8192)),
        },
    }
    if config.get("num_gpu") is not None:
        payload["options"]["num_gpu"] = int(config["num_gpu"])
    return _execute_ollama_call(config["api_base"], payload, event_file, session_id, "qwen")


def _call_deepseek(config: dict, prompt: str, max_tokens: int, event_file: Path, session_id: dict) -> tuple[str, bool, dict]:
    api_key = get_env(str(config.get("api_key_env", "DEEPSEEK_API_KEY")))
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set in environment")
    payload = {
        "model": config.get("model", "deepseek-chat"),
        "messages": [
            {"role": "system", "content": "You are a flexible research, writing, and review assistant."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": float(config.get("temperature", 0.3)),
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    return _execute_http_call(config["api_base"], payload, headers, event_file, session_id, "deepseek")


def _call_glm(config: dict, prompt: str, max_tokens: int, event_file: Path, session_id: dict) -> tuple[str, bool, dict]:
    api_key = get_env(str(config.get("api_key_env", "GLM_API_KEY")))
    if not api_key:
        raise RuntimeError("GLM_API_KEY not set in environment")
    payload = {
        "model": config.get("model", "glm-4"),
        "messages": [
            {"role": "system", "content": "You are a flexible research, writing, and review assistant."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": float(config.get("temperature", 0.3)),
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    return _execute_http_call(config["api_base"], payload, headers, event_file, session_id, "glm")


def _call_claude(config: dict, prompt: str, max_tokens: int, event_file: Path, session_id: dict) -> tuple[str, bool, dict]:
    append_wrapper_event(event_file, "stage.provider_called", {"model": "claude", "api_base": "not_configured"})
    append_wrapper_event(event_file, "stage.completed", {"model": "claude", "usage_source": "none"})
    return f"[Claude API not configured]\n\n{prompt}", False, {}


def _execute_ollama_call(url: str, payload: dict, event_file: Path, session_id: dict, model: str) -> tuple[str, bool, dict]:
    append_wrapper_event(event_file, "stage.provider_called", {"model": model, "api_base": url, **session_id})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener.open(request, timeout=300) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc)) from exc

    # Support both /api/chat and /api/generate response formats
    if "message" in body:
        result = body["message"].get("content", "").strip()
    else:
        result = body.get("response", "").strip()
    if not result:
        raise RuntimeError(f"Unexpected response shape: {body}")

    was_truncated = body.get("done_reason") == "length" or result.endswith("...")
    usage = {
        "tokens_in": body.get("prompt_eval_count"),
        "tokens_out": body.get("eval_count"),
        "usage_source": "ollama",
    }
    append_wrapper_event(event_file, "stage.completed", {"model": model, **usage, **session_id})
    return result, was_truncated, usage


def _execute_http_call(
    url: str,
    payload: dict,
    headers: dict,
    event_file: Path,
    session_id: dict,
    model: str,
) -> tuple[str, bool, dict]:
    append_wrapper_event(event_file, "stage.provider_called", {"model": model, "api_base": url, **session_id})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    max_attempts = 5
    body: dict[str, Any] | None = None

    for attempt in range(1, max_attempts + 1):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with opener.open(request, timeout=300) as response:
                body = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            is_rate_limited = exc.code == 429
            if is_rate_limited and attempt < max_attempts:
                wait_seconds = min(30, 2 ** (attempt - 1))
                append_wrapper_event(
                    event_file,
                    "stage.rate_limited",
                    {
                        "model": model,
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "wait_seconds": wait_seconds,
                        "error": detail,
                        **session_id,
                    },
                )
                time.sleep(wait_seconds)
                continue
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(str(exc)) from exc

    if body is None:
        raise RuntimeError(f"{model} request failed after {max_attempts} attempts")

    try:
        choice = body["choices"][0]
        result = choice["message"]["content"].strip()
    except Exception as exc:
        raise RuntimeError(f"Unexpected response shape: {body}") from exc

    usage_info = body.get("usage") or {}
    usage = {
        "tokens_in": usage_info.get("prompt_tokens"),
        "tokens_out": usage_info.get("completion_tokens"),
        "usage_source": "api",
    }
    was_truncated = choice.get("finish_reason") == "length" or result.endswith("...")
    append_wrapper_event(event_file, "stage.completed", {"model": model, **usage, **session_id})
    return result, was_truncated, usage


def main() -> int:
    parser = argparse.ArgumentParser(description="Universal multi-model wrapper")
    parser.add_argument("--model", required=True, choices=["qwen", "deepseek", "glm", "claude"])
    parser.add_argument("--task", required=True, choices=["reason", "write", "review", "execute", "continue"])
    parser.add_argument("--read-file")
    parser.add_argument("--write-file", required=True)
    parser.add_argument("--append-file")
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--continue-from")
    parser.add_argument("--session-id")
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--stage-name")
    parser.add_argument("--config-file")
    args = parser.parse_args()

    try:
        model_config = get_model_config(args.model, args.config_file)
    except KeyError:
        if args.model == "claude":
            model_config = {}
        else:
            raise
    max_tokens = args.max_tokens or int(model_config.get("max_tokens", model_config.get("num_predict", 3000)))

    state = None
    if args.session_id:
        _project_root = Path(__file__).resolve().parent.parent.parent.parent
        session_dir = _project_root / "workspace" / "sessions" / args.session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        state = TaskState(session_dir)
        if args.stage_name:
            state.set_stage_status(args.stage_name, "in_progress", args.model)

    prompt = Path(args.prompt_file).read_text(encoding="utf-8") if args.prompt_file else (args.prompt or "")
    if not prompt and args.task != "continue":
        defaults = {
            "reason": "Analyze the task and produce a reasoning memo.",
            "write": "Write the requested content.",
            "review": "Review the provided content.",
            "execute": "Execute the requested task.",
        }
        prompt = defaults[args.task]

    existing_output = None
    if args.task == "continue" and Path(args.write_file).exists():
        existing_output = Path(args.write_file).read_text(encoding="utf-8")

    full_prompt = build_prompt(args.task, prompt, args.read_file, args.continue_from, existing_output)

    try:
        content, was_truncated, _usage = call_model(args.model, model_config, full_prompt, max_tokens, args.session_id)
    except Exception as exc:
        if state and args.stage_name:
            state.set_stage_status(args.stage_name, f"failed: {exc}", args.model)
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_manager = OutputManager(Path(args.write_file), Path(args.append_file) if args.append_file else None)
    mode = "continue" if args.task == "continue" else "write"
    was_truncated, bytes_written = output_manager.write_output(content, mode=mode, truncate_marker=args.continue_from)

    print(f"Output written to: {args.write_file}")
    print(f"Bytes written: {bytes_written}")
    if was_truncated:
        print("Warning: Output appears truncated. Use --task continue to resume.")
        if state:
            state.set_continuation_marker(args.continue_from or "auto", bytes_written)

    if state and args.stage_name:
        state.set_stage_status(args.stage_name, "completed", args.model)
        state.register_artifact(args.stage_name, Path(args.write_file), f"Output from {args.model}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
