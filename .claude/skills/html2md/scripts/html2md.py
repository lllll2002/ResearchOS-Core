"""
html2md — Convert HTML files to clean Markdown.
Optimized for WeChat articles but works with any HTML.
"""

import sys
import io
import argparse
import subprocess
from pathlib import Path

# Fix Windows GBK encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def ensure_deps():
    """Auto-install missing dependencies."""
    for pkg, import_name in [("beautifulsoup4", "bs4"), ("markdownify", "markdownify")]:
        try:
            __import__(import_name)
        except ImportError:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg, "-q"],
                stdout=subprocess.DEVNULL,
            )


ensure_deps()

from bs4 import BeautifulSoup
from markdownify import markdownify as md


def convert(html_path: str, keep_images: bool = False, max_lines: int = 0) -> str:
    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content tags
    strip_tags = ["script", "style", "svg", "link", "meta", "noscript"]
    if not keep_images:
        strip_tags.append("img")
    for tag in soup.find_all(strip_tags):
        tag.decompose()

    # Try to extract article body (WeChat / common blog structures)
    body = (
        soup.find("div", id="js_content")              # WeChat
        or soup.find("div", class_="rich_media_content")  # WeChat alt
        or soup.find("article")                          # Generic blog
        or soup.find("div", class_="post-content")       # WordPress etc.
        or soup.find("div", class_="entry-content")      # WordPress alt
        or soup.body
        or soup
    )

    result = md(str(body), heading_style="ATX")

    # Clean up: remove empty/whitespace-only lines, strip each line
    lines = [line.strip() for line in result.splitlines() if line.strip()]
    # Filter out very short noise lines (CSS fragments, stray punctuation)
    lines = [l for l in lines if len(l) > 3 or l.startswith("#")]

    if max_lines > 0:
        lines = lines[:max_lines]

    return "\n\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Convert HTML to clean Markdown")
    parser.add_argument("input", help="Path to HTML file")
    parser.add_argument("-o", "--output", help="Save to .md file")
    parser.add_argument("--keep-images", action="store_true", help="Keep image alt text")
    parser.add_argument("--max-lines", type=int, default=0, help="Limit output lines")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    result = convert(args.input, args.keep_images, args.max_lines)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Saved: {out_path}")
    else:
        print(result)


if __name__ == "__main__":
    main()
