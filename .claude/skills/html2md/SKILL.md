---
name: html2md
description: "Convert HTML files to clean Markdown. Use this skill whenever the user wants to extract readable content from an HTML file, convert a saved web page to Markdown, clean up a downloaded article, or process WeChat/公众号 articles. Triggers on: 'html to markdown', 'convert this html', 'extract this webpage', '提取网页内容', '转成markdown', or any request involving .html files that need content extraction."
---

# HTML to Markdown Converter

Convert saved HTML files (web pages, WeChat articles, blog posts) into clean, readable Markdown.

## How it works

1. Read the HTML file
2. Clean it with BeautifulSoup (strip scripts, styles, images, SVG, meta tags)
3. For WeChat/公众号 articles, extract only the article body (`js_content` or `rich_media_content`)
4. Convert to Markdown with `markdownify`
5. Remove empty lines and noise, output clean text

## Usage

The user provides an HTML file path. Run the conversion script:

```bash
python "E:/Obsidian/.claude/skills/html2md/scripts/html2md.py" "<input.html>"
```

To save as .md file:

```bash
python "E:/Obsidian/.claude/skills/html2md/scripts/html2md.py" "<input.html>" -o "<output.md>"
```

### Options

| Flag | Description |
|------|-------------|
| (positional) | Input HTML file path (required) |
| `-o`, `--output` | Save output to .md file instead of printing to stdout |
| `--keep-images` | Keep image alt text in output (default: strip images) |
| `--max-lines N` | Limit output to first N non-empty lines (default: unlimited) |

### Dependencies

Requires `beautifulsoup4` and `markdownify`. The script auto-installs them if missing.

## When the user just wants to see content

Print the result directly in the conversation. If the content is long (>100 lines), show a summary of the first ~50 lines and ask if they want the full text or to save as .md.

## When the user wants to save

Use the `-o` flag to write a .md file. Default output location: same directory as the input file, with `.md` extension replacing `.html`.
