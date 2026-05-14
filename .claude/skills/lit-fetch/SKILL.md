---
name: lit-fetch
description: Download paper PDFs and queue for ScholarAIO ingest. Trigger on "download paper", "fetch paper", "get PDF", "scihub", or when given DOIs/titles to download. Supports single and batch mode.
allowed-tools: Bash, Read, Write, Glob
---

# lit-fetch -- Paper PDF Download

**Incoming folder:** `E:\Obsidian\Scholaraio\incoming\`
**Ingest inbox:** `E:\Obsidian\Scholaraio\scholaraio-main\data\inbox\`

---

## Cascade Strategy (ALWAYS follow this order)

For each paper, try sources in this EXACT order. Stop on first success.

```
1. Unpaywall (OA direct link)         -- scihub_fetch.py handles this
2. Publisher OA direct link            -- see table below
3. arXiv (if preprint exists)          -- arxiv.org/pdf/{id}.pdf
4. Sci-Hub via Playwright (sci-hub.ru) -- PROVEN WORKING method
5. 科研通 (ablesci)                    -- LAST RESORT, requires title not DOI
```

**CRITICAL LESSONS (proven 2026-05-05):**
- `requests`/`curl` CANNOT download from Sci-Hub — DDoS-Guard blocks non-browser clients.
- **Playwright headless Chrome is the only working method** for Sci-Hub in this environment.
- `sci-hub.ru` is the only mirror that resolves AND responds from China (system DNS works, no override needed).
- New Sci-Hub layout uses `<meta name="citation_pdf_url">` (NOT `<embed id="pdf">`).
- PDF CDN is on `sci-hub.cat` domain — direct fetch fails, must use browser download button (`.download a`).
- `scihub.net.cn` is just a JS redirect to sci-hub.ru — not a real mirror, POST form won't work via curl.
- 科研通 (`ablesci_fetch.py`) requires PAPER TITLE, not DOI.

---

## Single Paper Download

### Step 1: Identify input
- DOI (e.g., `10.1038/s41593-024-01626-2`) -- most reliable
- Title (e.g., "Spike sorting biases in cortical model") -- needed for ablesci
- URL (extract DOI from it)

### Step 2: Try scihub_fetch.py first (handles Unpaywall → PMC → arXiv)
```bash
python "E:/Obsidian/scripts/scihub_fetch.py" "<DOI>"
```
If successful: PDF lands in `incoming/`. Done.
If it reaches Sci-Hub stage and fails (DDoS-Guard): proceed to Step 3.

### Step 3: Playwright download (proven method for Sci-Hub)
```python
from playwright.sync_api import sync_playwright
from pathlib import Path
import time

DOI = "<DOI>"
SAVE = Path("E:/Obsidian/Scholaraio/incoming") / f"{DOI.replace('/', '_')}.pdf"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    page.goto(f"https://sci-hub.ru/{DOI}", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    # Click download button (triggers browser-native download, bypasses CDN restrictions)
    dl_btn = page.query_selector('.download a, a[href*="storage"], a[href*=".pdf"]')
    if dl_btn:
        with page.expect_download(timeout=60000) as dl_info:
            dl_btn.click()
        dl_info.value.save_as(str(SAVE))
        print(f"OK: {SAVE.stat().st_size // 1024} KB")
    else:
        print("NOT FOUND on Sci-Hub")
    browser.close()
```
Verify: first 4 bytes must be `%PDF`. If HTML, delete and try Step 4.

### Step 4: If failed, try 科研通 with TITLE
```bash
python "E:/Obsidian/scripts/ablesci_fetch.py" "<PAPER TITLE>"
```
**NOT DOI.** Use Crossref API to resolve real title first if needed.

### Step 5: Verify and move to paper directory
```python
import json, shutil
from pathlib import Path

PAPERS = Path("E:/Obsidian/Scholaraio/scholaraio-main/data/papers")
# Find paper dir by DOI from meta.json
for meta_path in PAPERS.glob("*/meta.json"):
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("doi", "").lower() == DOI.lower():
        uuid = meta["id"]
        target = meta_path.parent / f"{uuid}_origin.pdf"
        shutil.move(str(SAVE), str(target))
        print(f"Moved to: {target}")
        break
```

---

## Batch Download

### Preferred script: `batch_scihub.py`

Location: `E:\Obsidian\Scholaraio\incoming\batch_scihub.py`

```bash
# Generate DOI list from failed papers
grep "^FAIL\|^TIMEOUT" "E:/Obsidian/Scholaraio/incoming/batch_fetch_log.txt" | cut -f2 > failed_dois.txt

# Run batch (Playwright + sci-hub.ru, auto-moves to paper dirs)
python "E:/Obsidian/Scholaraio/incoming/batch_scihub.py" failed_dois.txt --delay 5
```

Parameters:
- `--limit N` — process only first N papers
- `--offset M` — skip first M papers
- `--delay S` — seconds between requests (default 4, recommend 5)
- `-m MIRROR` — Sci-Hub mirror (default: sci-hub.ru)

The script:
1. Opens headless Chrome via Playwright
2. For each DOI: navigates to sci-hub.ru/{DOI}
3. Clicks `.download a` button → `expect_download` → saves PDF
4. Auto-moves PDF to correct `data/papers/{name}/{uuid}_origin.pdf`
5. Logs results to `batch_scihub_log.txt`
6. Saves still-failed DOIs to `still_failed_dois.txt`

### Alternative: scihub_fetch.py batch (for OA papers)

For papers likely to be open access (Unpaywall/PMC/arXiv):
```bash
python "E:/Obsidian/Scholaraio/incoming/batch_fetch_missing.py" --delay 4
```
This uses `scihub_fetch.py` cascade (fast for OA, but fails on paywalled papers).

---

## After Download: Full Ingest (MinerU reparse)

Downloaded PDFs are just stored files. For full ingest (paper.md + images):

```bash
# Single paper
cd "E:/Obsidian/Scholaraio/scholaraio-main"
scholaraio attach-pdf "<paper-dir-name>" "<external-pdf-path>"

# Batch reparse (for PDFs already in paper dirs)
cd "E:/Obsidian/Scholaraio/scholaraio-main"
python "E:/Obsidian/Scholaraio/incoming/batch_reparse.py" --delay 3
```

Requires MinerU (local `http://localhost:8000` or cloud API with key).

---

## Publisher OA Direct Links

| Publisher | DOI prefix | Direct PDF pattern |
|-----------|-----------|-------------------|
| Wiley | `10.1002/` | `onlinelibrary.wiley.com/doi/pdfdirect/<DOI>` |
| Frontiers | `10.3389/` | `frontiersin.org/articles/<DOI>/pdf` |
| MDPI | `10.3390/` | `mdpi.com/<DOI>/pdf` |
| PLOS | `10.1371/` | journals API |
| eLife | `10.7554/` | `elifesciences.org/articles/<ID>.pdf` |
| bioRxiv | `10.1101/` | `biorxiv.org/content/<DOI>v2.full.pdf` |
| PNAS | `10.1073/` | `pnas.org/doi/pdf/<DOI>` |

---

## Debugging with playwright-cli

When Sci-Hub downloads fail or selectors change, use `playwright-cli` for quick diagnosis:

```bash
# Open Sci-Hub page in headed mode to see what's happening
playwright-cli open --headed "https://sci-hub.ru/10.1038/s41593-024-01626-2"

# Snapshot DOM to find current selectors (they change over time)
playwright-cli snapshot

# Test a selector
playwright-cli click <ref-from-snapshot>

# Check what DDoS-Guard is doing
playwright-cli --raw eval "document.title + ' | ' + document.querySelector('.download a')?.href"
```

This is faster than writing/modifying Python scripts for debugging. Use Python Playwright for actual batch downloads.

---

## Known Issues and Workarounds

| Issue | Workaround |
|-------|-----------|
| Sci-Hub DDoS-Guard blocks requests/curl | **Use Playwright** (proven working) |
| sci-hub.cat CDN not accessible | Click `.download a` button instead of direct URL fetch |
| sci-hub.se/st/ee DNS blocked or unresponsive | Use `sci-hub.ru` only (direct China access) |
| scihub.net.cn returns 404 on direct DOI | It's just a JS redirect, not a real API — use sci-hub.ru |
| "article not found" on Sci-Hub | Paper not in Sci-Hub DB, use ablesci |
| ablesci rejects DOI as title | Use Crossref API to resolve real title first |
| PDF is actually HTML (login page) | Verify %PDF header, delete fakes |
| Playwright not installed | `pip install playwright && python -m playwright install chromium` |
| Selector debugging needed | Use `playwright-cli open --headed` + `snapshot` for live inspection |
