"""
run_morning_setup.py — Automated daily plan generation via Claude CLI
=====================================================================

1. Archive yesterday's today.md → 01_Planning/archive/YYYY-MM-DD.md
2. Call Claude Code CLI with /morning-setup to generate new today.md

Designed for Windows Task Scheduler (07:30 daily).

Usage:
    python run_morning_setup.py           # run morning setup
    python run_morning_setup.py --dry-run # show what would run, don't execute
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

VAULT = Path(r"E:\Obsidian")
TODAY_FILE = VAULT / "01_Planning" / "today.md"
ARCHIVE_DIR = VAULT / "01_Planning" / "archive"
LOG_DIR = VAULT / "07_System_Optimization" / "generated" / "logs"
LOCK_FILE = LOG_DIR / "morning_setup.lock"

CLAUDE_PATHS = [
    r"C:\Users\Administrator\.claude\local\claude.exe",
    r"C:\Users\Administrator\AppData\Local\Programs\claude\claude.exe",
    r"C:\Program Files\Claude\claude.exe",
]


def find_claude() -> str:
    claude_in_path = shutil.which("claude")
    if claude_in_path:
        return claude_in_path
    for p in CLAUDE_PATHS:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError("Claude CLI not found. Install it or add to PATH.")


def setup_logging():
    timestamp = datetime.now().strftime("%Y-%m-%d")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / f"morning_setup_{timestamp}.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def acquire_lock() -> bool:
    if LOCK_FILE.exists():
        age = datetime.now().timestamp() - LOCK_FILE.stat().st_mtime
        if age < 900:
            logging.warning("Lock file exists and is recent (%d sec). Skipping.", int(age))
            return False
        logging.info("Stale lock file (%d sec). Removing.", int(age))
        LOCK_FILE.unlink()
    LOCK_FILE.write_text(str(os.getpid()))
    return True


def release_lock():
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


def archive_today():
    """Archive yesterday's today.md to 01_Planning/archive/YYYY-MM-DD.md"""
    if not TODAY_FILE.exists():
        logging.info("No today.md to archive.")
        return

    content = TODAY_FILE.read_text(encoding="utf-8")
    if not content.strip():
        logging.info("today.md is empty, skipping archive.")
        return

    # Extract date from frontmatter (date: YYYY-MM-DD)
    archive_date = None
    for line in content.split("\n")[:10]:
        if line.strip().startswith("date:"):
            date_str = line.split(":", 1)[1].strip().strip('"').strip("'")
            archive_date = date_str
            break

    if not archive_date:
        # Fallback: use yesterday's date
        archive_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        logging.warning("No date in frontmatter, using yesterday: %s", archive_date)

    # Don't archive if it's already today's date (re-run protection)
    today_str = datetime.now().strftime("%Y-%m-%d")
    if archive_date == today_str:
        logging.info("today.md date matches today (%s), skipping archive.", today_str)
        return

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = ARCHIVE_DIR / f"{archive_date}.md"

    if archive_path.exists():
        logging.info("Archive %s already exists, overwriting.", archive_path.name)

    shutil.copy2(TODAY_FILE, archive_path)
    logging.info("Archived today.md → %s", archive_path)


def run_morning_setup(dry_run: bool = False):
    setup_logging()
    logging.info("=== Morning Setup started ===")

    if not acquire_lock():
        return 1

    try:
        # Step 1: Archive yesterday's today.md
        logging.info("Step 1: Archiving yesterday's today.md...")
        if dry_run:
            logging.info("[DRY RUN] Would archive today.md")
        else:
            archive_today()

        # Step 2: Call Claude CLI to generate new today.md
        claude_exe = find_claude()
        logging.info("Step 2: Calling Claude CLI...")
        logging.info("Claude CLI: %s", claude_exe)

        prompt = "/morning-setup"
        cmd = [
            claude_exe,
            "-p", prompt,
            "--allowedTools", "Read,Write,Edit,Glob,Grep,Bash",
            "--max-turns", "30",
        ]

        logging.info("Command: %s", " ".join(cmd))

        if dry_run:
            logging.info("[DRY RUN] Would execute the above command.")
            return 0

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,  # 5 min max
            cwd=str(VAULT),
            env=env,
        )

        if result.stdout:
            logging.info("STDOUT:\n%s", result.stdout[-2000:])
        if result.stderr:
            logging.warning("STDERR:\n%s", result.stderr[-1000:])

        if result.returncode == 0:
            logging.info("Morning setup completed successfully.")
        else:
            logging.error("Morning setup failed with exit code %d", result.returncode)

        return result.returncode

    except FileNotFoundError as e:
        logging.error("Claude CLI not found: %s", e)
        return 2
    except subprocess.TimeoutExpired:
        logging.error("Morning setup timed out (5 min).")
        return 3
    except Exception as e:
        logging.error("Unexpected error: %s", e)
        return 4
    finally:
        release_lock()
        logging.info("=== Morning Setup finished ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run morning-setup via Claude CLI")
    parser.add_argument("--dry-run", action="store_true", help="Show command without executing")
    args = parser.parse_args()
    sys.exit(run_morning_setup(dry_run=args.dry_run))
