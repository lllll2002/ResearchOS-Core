from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from _common import append_wrapper_event, build_round_header, default_reasoning_prompt, extract_usage_ollama, load_config, wrapper_event_path

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent.parent.parent / "workspace" / "current_task" / "20_reasoning.md"


class WrapperError(Exception):
    pass


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    if args.prompt:
        return args.prompt
    data = sys.stdin.read().strip()
    if data:
        return data
    try:
        return default_reasoning_prompt()
    except ValueError as exc:
        raise WrapperError(str(exc)) from exc


def call_ollama(url: str, model: str, prompt: str, temperature: float, num_predict: int, num_ctx: int | None = None, num_gpu: int | None = None) -> tuple[str, dict]:
    options: dict = {
        "temperature": temperature,
        "num_predict": num_predict,
    }
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    if num_gpu is not None:
        options["num_gpu"] = num_gpu
    payload = {
        "model": model,
        "prompt": (
            "You are the Qwen local reasoning stage. Produce a concise reasoning memo with assumptions, edge cases, "
            "failure modes, recommended path, and rejected paths.\n\n" + prompt
        ),
        "stream": False,
        "options": options,
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # Bypass system proxy for local Ollama — system proxy (e.g. VPN) returns 502 for localhost.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if "memory layout cannot be allocated" in detail:
            raise WrapperError(
                f"HTTP {exc.code}: CUDA memory allocation failed for model '{model}'.\n"
                "Likely cause: Ollama version does not support this GPU architecture (e.g. RTX 5070 / Blackwell SM_100).\n"
                "Fix: upgrade Ollama to the latest version (winget upgrade Ollama.Ollama)."
            ) from exc
        raise WrapperError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise WrapperError(str(exc)) from exc
    result = body.get("response", "").strip()
    if not result:
        raise WrapperError(f"Unexpected response shape: {body}")
    return result, extract_usage_ollama(body)


def render_markdown(model: str, prompt: str, content: str) -> str:
    return f"""# Reasoning Memo\n\n## Stage\nQwen local reasoning\n\n## Model\n{model}\n\n## Input Summary\n{prompt[:800].strip()}\n\n## Reasoning Output\n\n{content}\n"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Qwen reasoning stage and write 20_reasoning.md.")
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--round", type=int, dest="round_num", help="Team-mode round number (enables round header)")
    parser.add_argument("--round-speaker", default="qwen3:8b", help="Speaker model name for round header")
    parser.add_argument("--round-reasoning", default="", help="Router reasoning sentence for round header")
    parser.add_argument("--round-prior-artifacts", default="none", help="Prior artifacts read, for round header")
    parser.add_argument("--session-id", default=None, help="Pipeline session ID for grouping runs in Bridge Live v2")
    args = parser.parse_args()

    prompt = read_prompt(args)
    config = load_config()["qwen_reason"]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    event_file = wrapper_event_path("qwen")

    round_header = ""
    if args.round_num is not None:
        round_header = build_round_header(
            args.round_num, args.round_speaker, args.round_reasoning, args.round_prior_artifacts
        )

    if args.dry_run:
        body = render_markdown(config["model"], prompt, "Dry-run only. No local model call was made.")
        output.write_text(round_header + body if round_header else body, encoding="utf-8", newline="\n")
        print(output)
        return 0

    sid = {"session_id": args.session_id} if args.session_id else {}
    append_wrapper_event(event_file, "stage.started", {"model": "qwen", "config_model": config["model"], "output_path": str(output), **sid})
    try:
        append_wrapper_event(event_file, "stage.provider_called", {"model": "qwen", "api_base": config["api_base"]})
        num_ctx_val = config.get("num_ctx")
        num_gpu_val = config.get("num_gpu")
        content, usage = call_ollama(
            config["api_base"],
            config["model"],
            prompt,
            float(config.get("temperature", 0.2)),
            int(config.get("num_predict", 3000)),
            num_ctx=int(num_ctx_val) if num_ctx_val is not None else None,
            num_gpu=int(num_gpu_val) if num_gpu_val is not None else None,
        )
        body = render_markdown(config["model"], prompt, content)
        output.write_text(round_header + body if round_header else body, encoding="utf-8", newline="\n")
        append_wrapper_event(event_file, "output.written", {"model": "qwen", "output_path": str(output)})
        append_wrapper_event(event_file, "stage.completed", {"model": "qwen", "output_path": str(output), **usage})
        append_wrapper_event(event_file, "stage.usage_emitted", {
            "model": "qwen",
            "has_usage": usage.get("tokens_in") is not None or usage.get("tokens_out") is not None,
            "tokens_in": usage.get("tokens_in"),
            "tokens_out": usage.get("tokens_out"),
            "usage_source": usage.get("usage_source"),
        })
    except Exception as exc:
        append_wrapper_event(event_file, "stage.failed", {"model": "qwen", "error": str(exc)})
        raise
    print(output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WrapperError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
