"""Gamma PPT generator — calls Gamma REST API to create a presentation.

Usage:
    python scripts/gamma_ppt.py --text "slide content..." [options]

Options:
    --text TEXT          Input text for slide generation (required)
    --title TITLE        Presentation title (optional)
    --mode MODE          textMode: generate | condense | preserve (default: generate)
    --cards N            Number of slides/cards (default: auto)
    --lang LANG          Language code, e.g. zh-CN, en-US (default: zh-CN)
    --export             Also export as PPTX and print download URL
    --config PATH        Path to config.local.yaml (default: auto-detect)
"""

import argparse
import sys
import time
from pathlib import Path

import requests
import yaml


def load_api_key(config_path: str | None = None) -> str:
    """Load Gamma API key from config.local.yaml."""
    if config_path:
        p = Path(config_path)
    else:
        # Auto-detect: walk up from this script's location
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        p = project_root / "config.local.yaml"

    if not p.exists():
        print(f"[ERROR] Config file not found: {p}", file=sys.stderr)
        sys.exit(1)

    with open(p, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    key = cfg.get("gamma", {}).get("api_key", "")
    if not key:
        print("[ERROR] gamma.api_key not found in config.local.yaml", file=sys.stderr)
        sys.exit(1)
    return key


def generate_presentation(
    api_key: str,
    input_text: str,
    title: str | None = None,
    text_mode: str = "generate",
    num_cards: int | None = None,
    language: str = "zh-CN",
    export_pptx: bool = False,
) -> dict:
    """Call Gamma API to generate a presentation.

    Returns dict with keys: generationId, gammaUrl, pptxUrl (if requested).
    """
    base_url = "https://public-api.gamma.app/v1.0"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    # Build request body
    body: dict = {
        "inputText": input_text,
        "textMode": text_mode,
    }
    if num_cards:
        body["numCards"] = num_cards
    if export_pptx:
        body["exportAs"] = "pptx"

    print("[1/3] Submitting generation request to Gamma API...")
    resp = requests.post(f"{base_url}/generations", json=body, headers=headers, timeout=30)

    if resp.status_code not in (200, 201):
        print(f"[ERROR] API request failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    generation_id = data.get("generationId") or data.get("id")
    if not generation_id:
        print(f"[ERROR] No generationId in response: {data}", file=sys.stderr)
        sys.exit(1)

    print(f"[2/3] Generation started (id={generation_id}). Polling for completion...")

    # Poll until completed
    max_wait = 300  # 5 minutes
    interval = 5
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(interval)
        elapsed += interval

        poll = requests.get(
            f"{base_url}/generations/{generation_id}",
            headers=headers,
            timeout=15,
        )
        if poll.status_code != 200:
            print(f"[WARN] Poll failed ({poll.status_code}), retrying...")
            continue

        result = poll.json()
        status = result.get("status", "")
        print(f"  status={status} ({elapsed}s elapsed)")

        if status == "completed":
            gamma_url = result.get("gammaUrl") or result.get("url", "")
            pptx_url = result.get("pptxUrl") or result.get("exportUrl", "")
            return {
                "generationId": generation_id,
                "gammaUrl": gamma_url,
                "pptxUrl": pptx_url,
                "status": "completed",
            }
        elif status in ("failed", "error"):
            print(f"[ERROR] Generation failed: {result}", file=sys.stderr)
            sys.exit(1)

    print("[ERROR] Timed out waiting for generation to complete.", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate a Gamma presentation from text")
    parser.add_argument("--text", required=True, help="Input text for slide generation")
    parser.add_argument("--title", default=None, help="Presentation title")
    parser.add_argument(
        "--mode",
        default="generate",
        choices=["generate", "condense", "preserve"],
        help="Text mode (default: generate)",
    )
    parser.add_argument("--cards", type=int, default=None, help="Number of slides")
    parser.add_argument("--lang", default="zh-CN", help="Language code (default: zh-CN)")
    parser.add_argument("--export", action="store_true", help="Also export PPTX")
    parser.add_argument("--config", default=None, help="Path to config.local.yaml")
    args = parser.parse_args()

    api_key = load_api_key(args.config)
    result = generate_presentation(
        api_key=api_key,
        input_text=args.text,
        title=args.title,
        text_mode=args.mode,
        num_cards=args.cards,
        language=args.lang,
        export_pptx=args.export,
    )

    print("\n[3/3] Done!")
    print(f"  Gamma URL : {result['gammaUrl']}")
    if result.get("pptxUrl"):
        print(f"  PPTX URL  : {result['pptxUrl']}")
    print(f"  ID        : {result['generationId']}")


if __name__ == "__main__":
    main()
