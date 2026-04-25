"""
health_daemon.py — Automated system health monitor (hardened)
==============================================================

7 checks + 4 auto-repairs + lock + cooldown + verification + escalation.

Usage:
    python health_daemon.py              # full check + repair
    python health_daemon.py --check-only # report only, no repair
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT = Path(os.environ.get("RESEARCH_OS_VAULT", PROJECT_ROOT / "vault"))
SA_ROOT = PROJECT_ROOT
DATA = SA_ROOT / "data"
BACKUP_LOG = Path(os.environ.get("RESEARCH_OS_BACKUP_LOG", SA_ROOT / "backups" / "backup_log.txt"))
CONTEXT_FILE = VAULT / "01_Planning" / "AI_active_context.md"
GENERATED = PROJECT_ROOT / "generated"
EVENT_LOG = GENERATED / "health_event_log.jsonl"
LOCK_FILE = GENERATED / "health_daemon.lock"
COOLDOWN_FILE = GENERATED / "health_cooldown.json"

# Cooldown durations in hours
COOLDOWN_HOURS = {
    "index": 6,
    "kg": 6,
    "benchmark": 6,
    "backup": 12,
    # git: no cooldown (check-only, never repaired)
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("health")


# =========================================================================
#  Event logging
# =========================================================================

def _log_event(event_type: str, component: str, detail: dict):
    """Append a structured event to JSONL log."""
    GENERATED.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(),
        "type": event_type,  # check, skip, repair, verify, escalate
        "component": component,
        **detail,
    }
    with open(EVENT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# =========================================================================
#  Lock
# =========================================================================

def _acquire_lock() -> bool:
    """Try to acquire global lock. Returns False if already locked."""
    if LOCK_FILE.exists():
        # Check if lock is stale (>30 min)
        age = datetime.now().timestamp() - LOCK_FILE.stat().st_mtime
        if age > 1800:
            LOCK_FILE.unlink()
            _log_event("lock", "global", {"action": "stale_lock_cleared", "age_sec": round(age)})
        else:
            return False
    LOCK_FILE.write_text(str(os.getpid()), "utf-8")
    return True


def _release_lock():
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


# =========================================================================
#  Cooldown
# =========================================================================

def _load_cooldowns() -> dict:
    if COOLDOWN_FILE.exists():
        try:
            return json.loads(COOLDOWN_FILE.read_text("utf-8"))
        except Exception:
            return {}
    return {}


def _save_cooldowns(cd: dict):
    COOLDOWN_FILE.write_text(json.dumps(cd), "utf-8")


def _in_cooldown(component: str) -> bool:
    cd = _load_cooldowns()
    last = cd.get(component)
    if not last:
        return False
    try:
        last_time = datetime.fromisoformat(last)
        hours = COOLDOWN_HOURS.get(component, 6)
        return datetime.now() - last_time < timedelta(hours=hours)
    except Exception:
        return False


def _set_cooldown(component: str):
    cd = _load_cooldowns()
    cd[component] = datetime.now().isoformat()
    _save_cooldowns(cd)


# =========================================================================
#  7 Checks (unchanged logic)
# =========================================================================

def check_index_freshness():
    faiss = DATA / "faiss.index"
    papers = DATA / "papers"
    if not faiss.exists() or not papers.exists():
        return {"status": "MISSING", "detail": "faiss.index or papers/ not found"}
    faiss_time = faiss.stat().st_mtime
    newest = max((d.stat().st_mtime for d in papers.iterdir() if d.is_dir()), default=0)
    stale = newest > faiss_time
    return {"status": "STALE" if stale else "OK", "faiss_age_hours": round((datetime.now().timestamp() - faiss_time) / 3600, 1), "papers_newer": stale}


def check_benchmark():
    hist = DATA / "benchmark_history.jsonl"
    if not hist.exists():
        return {"status": "MISSING"}
    lines = hist.read_text("utf-8").strip().split("\n")
    if not lines:
        return {"status": "MISSING"}
    last = json.loads(lines[-1])
    score = last.get("overall_score", 0)
    return {"status": "DRIFT" if score < 0.8 else "OK", "score": score, "timestamp": last.get("timestamp", "?")}


def check_kg():
    kg = DATA / "kg.json"
    if not kg.exists():
        return {"status": "MISSING"}
    size = kg.stat().st_size
    if size < 100:
        return {"status": "EMPTY", "size": size}
    try:
        data = json.loads(kg.read_text("utf-8"))
        return {"status": "OK", "entities": len(data.get("entities", {})), "relations": len(data.get("relations", [])), "size": size}
    except Exception as e:
        return {"status": "CORRUPT", "error": str(e)}


def check_backup():
    if not BACKUP_LOG.exists():
        return {"status": "NEVER"}
    lines = BACKUP_LOG.read_text("utf-8").strip().split("\n")
    if not lines:
        return {"status": "NEVER"}
    try:
        ts_str = lines[-1].split("|")[0].strip()
        last_time = datetime.strptime(ts_str, "%Y-%m-%d %H:%M")
        hours_ago = (datetime.now() - last_time).total_seconds() / 3600
        return {"status": "STALE" if hours_ago > 48 else "OK", "last_run": ts_str, "hours_ago": round(hours_ago, 1)}
    except Exception:
        return {"status": "OK", "last_line": lines[-1]}


def check_git():
    try:
        r = subprocess.run(["git", "status", "--porcelain"], cwd=VAULT, capture_output=True, text=True, timeout=10)
        lines = [l for l in r.stdout.strip().split("\n") if l]
        count = len(lines)
        stale = False
        if count > 20:
            r2 = subprocess.run(["git", "log", "-1", "--format=%ci"], cwd=VAULT, capture_output=True, text=True, timeout=5)
            if r2.stdout.strip():
                last_commit = datetime.fromisoformat(r2.stdout.strip().replace(" ", "T").rsplit("+", 1)[0])
                stale = (datetime.now() - last_commit).days > 3
        return {"status": "STALE" if stale else "DIRTY" if count > 50 else "OK", "uncommitted": count}
    except Exception:
        return {"status": "UNKNOWN"}


def check_disk():
    total, used, free = shutil.disk_usage("E:\\")
    pct = free / total * 100
    return {"status": "LOW" if pct < 10 else "OK", "free_gb": round(free / 1024**3, 1), "pct_free": round(pct, 1)}


def check_pending():
    pending = DATA / "pending"
    if not pending.exists():
        return {"status": "OK", "count": 0}
    count = len([d for d in pending.iterdir() if d.is_dir() and not d.name.startswith("_")])
    return {"status": "HIGH" if count > 200 else "OK", "count": count}


# =========================================================================
#  4 Repairs + verification
# =========================================================================

def repair_index(check_only: bool) -> dict:
    comp = "index"
    if check_only:
        _log_event("skip", comp, {"reason": "check-only"})
        return {"result": "skipped", "verified": False}
    if _in_cooldown(comp):
        _log_event("skip", comp, {"reason": "cooldown"})
        return {"result": "cooldown", "verified": False}

    _log_event("repair", comp, {"action": "start"})
    try:
        r = subprocess.run(
            [sys.executable, "-m", "scholaraio.cli", "pipeline", "--steps", "embed,chunks,index"],
            cwd=SA_ROOT, capture_output=True, text=True, timeout=600
        )
        ok = r.returncode == 0
    except Exception as e:
        _log_event("repair", comp, {"action": "error", "error": str(e)})
        return {"result": f"error: {e}", "verified": False}

    if not ok:
        _log_event("repair", comp, {"action": "failed", "stderr": r.stderr[:200]})
        return {"result": "failed", "verified": False}

    # Verification: command succeeded = repair verified
    # (The pipeline itself handles incremental logic — if nothing new, it's a no-op success)
    verified = True
    _log_event("verify", comp, {"passed": verified, "method": "return_code"})

    if verified:
        _set_cooldown(comp)
    return {"result": "repaired", "verified": verified}


def repair_kg(check_only: bool) -> dict:
    comp = "kg"
    if check_only:
        _log_event("skip", comp, {"reason": "check-only"})
        return {"result": "skipped", "verified": False}
    if _in_cooldown(comp):
        _log_event("skip", comp, {"reason": "cooldown"})
        return {"result": "cooldown", "verified": False}

    _log_event("repair", comp, {"action": "start"})
    try:
        r = subprocess.run(
            [sys.executable, "-m", "scholaraio.cli", "kg", "build"],
            cwd=VAULT, capture_output=True, text=True, timeout=120
        )
        ok = r.returncode == 0
    except Exception as e:
        _log_event("repair", comp, {"action": "error", "error": str(e)})
        return {"result": f"error: {e}", "verified": False}

    if not ok:
        _log_event("repair", comp, {"action": "failed"})
        return {"result": "failed", "verified": False}

    # Verification: kg.json should be >100 bytes and parseable
    v = check_kg()
    verified = v["status"] == "OK" and v.get("entities", 0) > 0
    _log_event("verify", comp, {"passed": verified, "entities": v.get("entities", 0)})

    if verified:
        _set_cooldown(comp)
    return {"result": "rebuilt", "verified": verified}


def repair_backup(check_only: bool) -> dict:
    comp = "backup"
    if check_only:
        _log_event("skip", comp, {"reason": "check-only"})
        return {"result": "skipped", "verified": False}
    if _in_cooldown(comp):
        _log_event("skip", comp, {"reason": "cooldown"})
        return {"result": "cooldown", "verified": False}

    _log_event("repair", comp, {"action": "start"})
    try:
        r = subprocess.run(
            [sys.executable, str(VAULT / "scripts" / "backup_scholaraio.py"), "--run"],
            capture_output=True, text=True, timeout=600
        )
        ok = r.returncode == 0
    except Exception as e:
        _log_event("repair", comp, {"action": "error", "error": str(e)})
        return {"result": f"error: {e}", "verified": False}

    # Verification: backup log should have a fresh entry
    v = check_backup()
    verified = v.get("hours_ago", 999) < 1
    _log_event("verify", comp, {"passed": verified, "hours_ago": v.get("hours_ago")})

    if verified:
        _set_cooldown(comp)
    return {"result": "completed" if ok else "failed", "verified": verified}


    # NOTE: git auto-commit intentionally removed from repair chain.
    # Git is check-only — dirty state surfaces as an alert, never auto-committed.


# =========================================================================
#  Dashboard injection
# =========================================================================

def inject_health_block(report: dict):
    if not CONTEXT_FILE.exists():
        return
    text = CONTEXT_FILE.read_text("utf-8")

    alerts = []
    for name, check in report["checks"].items():
        s = check.get("status", "?")
        if s not in ("OK", "UNKNOWN"):
            alerts.append(f"  - {name}: {s}")

    escalations = report.get("escalations", [])

    block = f"""## System Health (auto-updated by health_daemon)
- Last check: {report['timestamp'][:19]}
- Index: {report['checks']['index']['status']} | Benchmark: {report['checks']['benchmark'].get('score', '?')} | KG: {report['checks']['kg']['status']} ({report['checks']['kg'].get('entities', '?')} entities)
- Backup: {report['checks']['backup']['status']} ({report['checks']['backup'].get('hours_ago', '?')}h ago) | Disk: {report['checks']['disk'].get('free_gb', '?')} GB free
- Git: {report['checks']['git'].get('uncommitted', '?')} uncommitted | Pending: {report['checks']['pending'].get('count', '?')}"""

    if alerts:
        block += "\n- **Alerts:** " + ", ".join(a.strip("- ") for a in alerts)

    repair_notes = []
    for name, r in report.get("repairs", {}).items():
        res = r.get("result", "?")
        ver = "verified" if r.get("verified") else "UNVERIFIED"
        if res not in ("skipped", "cooldown"):
            repair_notes.append(f"{name}={res}({ver})")
    if repair_notes:
        block += "\n- **Repairs:** " + ", ".join(repair_notes)

    if escalations:
        block += "\n- **ESCALATIONS:** " + "; ".join(escalations)

    marker = "## System Health"
    next_section = "\n## "

    if marker in text:
        start = text.index(marker)
        rest = text[start + len(marker):]
        if next_section in rest:
            end = start + len(marker) + rest.index(next_section)
            text = text[:start] + block + "\n\n" + text[end:]
        else:
            text = text[:start] + block + "\n"
    else:
        sep = text.find("\n---\n")
        if sep != -1:
            pos = sep + 5
            text = text[:pos] + "\n" + block + "\n\n" + text[pos:]

    CONTEXT_FILE.write_text(text, "utf-8")


# =========================================================================
#  Status layer output
# =========================================================================

def _write_system_health(report: dict):
    """Write system_health.json + system_health.md from report."""
    issues = []
    for comp, check in report["checks"].items():
        s = check.get("status", "OK")
        if s in ("OK", "UNKNOWN"):
            continue
        repair = report.get("repairs", {}).get(comp, {})
        issues.append({
            "issue_id": f"{comp}_{s.lower()}",
            "severity": "critical" if s in ("MISSING", "CORRUPT", "DRIFT") else "warning",
            "component": comp,
            "message": f"{comp} is {s}",
            "action_attempted": repair.get("result") if repair else None,
            "action_result": repair.get("result") if repair else None,
            "verification_result": "pass" if repair.get("verified") else "fail" if repair else None,
            "escalated": comp in [e.split()[0] for e in report.get("escalations", [])],
        })

    has_critical = any(i["severity"] == "critical" for i in issues)
    has_warning = any(i["severity"] == "warning" for i in issues)
    overall = "critical" if has_critical else "warning" if has_warning else "healthy"

    health = {
        "generated_at": report["timestamp"],
        "overall_status": overall,
        "issues": issues,
    }

    (GENERATED / "system_health.json").write_text(
        json.dumps(health, indent=2, ensure_ascii=False), "utf-8"
    )

    # Markdown version
    md = [
        f"# System Health",
        f"",
        f"Generated: {report['timestamp'][:19]}",
        f"Overall: **{overall.upper()}**",
        f"",
    ]
    if not issues:
        md.append("All systems nominal.")
    else:
        md.append("| Component | Severity | Status | Repair | Verified |")
        md.append("|-----------|----------|--------|--------|----------|")
        for i in issues:
            ver = i["verification_result"] or "—"
            rep = i["action_result"] or "—"
            md.append(f"| {i['component']} | {i['severity']} | {i['message']} | {rep} | {ver} |")

    (GENERATED / "system_health.md").write_text("\n".join(md), "utf-8")


def _write_recommended_actions(report: dict):
    """Write recommended_actions.json + .md from report."""
    actions = []

    for comp, check in report["checks"].items():
        s = check.get("status", "OK")
        if s in ("OK", "UNKNOWN"):
            continue

        repair = report.get("repairs", {}).get(comp, {})
        repair_result = repair.get("result") if repair else None

        # Determine if human action needed
        if repair_result in ("repaired", "rebuilt", "completed") and repair.get("verified"):
            continue  # auto-fixed successfully, no human action
        if repair_result == "cooldown":
            continue  # will retry after cooldown expires
        if repair_result == "skipped":
            continue  # check-only mode, not actionable

        # Needs human attention
        if repair_result == "cooldown":
            continue  # already handled above
        if repair_result and not repair.get("verified"):
            reason = f"Auto-repair executed but verification failed (result: {repair_result})"
            step = f"Manually check {comp}, consider running `scholaraio benchmark` or inspecting data/"
        elif s in ("HIGH",):
            reason = f"{comp} count exceeds threshold ({check.get('count', '?')})"
            step = f"Review data/pending/ and process or archive old items"
        elif s == "STALE" and comp == "index":
            reason = "Index older than newest papers"
            step = "Run: scholaraio pipeline --steps embed,chunks,index"
        elif s in ("STALE", "NEVER") and comp == "backup":
            reason = f"Last backup {check.get('hours_ago', '?')}h ago"
            step = "Run: python scripts/backup_scholaraio.py --run"
        elif s in ("EMPTY", "CORRUPT", "MISSING") and comp == "kg":
            reason = f"Knowledge graph is {s}"
            step = "Run: scholaraio kg build"
        elif s == "STALE" and comp == "git":
            reason = f"{check.get('uncommitted', '?')} uncommitted files, no commit in >3 days"
            step = "Review changes and commit: git add <files> && git commit"
        elif s == "LOW" and comp == "disk":
            reason = f"Only {check.get('free_gb', '?')} GB free ({check.get('pct_free', '?')}%)"
            step = "Free disk space on E: drive"
        else:
            reason = f"{comp} reported {s}"
            step = f"Investigate {comp} manually"

        actions.append({
            "component": comp,
            "severity": "critical" if s in ("MISSING", "CORRUPT", "DRIFT") else "warning",
            "reason": reason,
            "recommended_step": step,
        })

    # JSON
    (GENERATED / "recommended_actions.json").write_text(
        json.dumps({"generated_at": report["timestamp"], "actions": actions},
                    indent=2, ensure_ascii=False), "utf-8"
    )

    # Markdown
    md = [
        "# Recommended Actions",
        "",
        f"Generated: {report['timestamp'][:19]}",
        "",
    ]
    if not actions:
        md.append("No manual actions recommended. All issues auto-resolved or within tolerance.")
    else:
        md.append(f"{len(actions)} action(s) requiring attention:\n")
        for i, a in enumerate(actions, 1):
            md.append(f"### {i}. [{a['severity'].upper()}] {a['component']}")
            md.append(f"- **Reason:** {a['reason']}")
            md.append(f"- **Action:** {a['recommended_step']}")
            md.append("")

    (GENERATED / "recommended_actions.md").write_text("\n".join(md), "utf-8")


# =========================================================================
#  Main orchestration
# =========================================================================

def run(check_only: bool = False):
    GENERATED.mkdir(parents=True, exist_ok=True)

    # Lock
    if not check_only:
        if not _acquire_lock():
            _log_event("skip", "global", {"reason": "locked"})
            log.info("Another instance running (locked). Exiting.")
            return None
    try:
        return _run_inner(check_only)
    finally:
        if not check_only:
            _release_lock()


def _run_inner(check_only: bool) -> dict:
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "check-only" if check_only else "full",
        "checks": {},
        "repairs": {},
        "escalations": [],
    }

    log.info("=== Health Check ===")

    # Run all checks
    report["checks"]["index"] = check_index_freshness()
    report["checks"]["benchmark"] = check_benchmark()
    report["checks"]["kg"] = check_kg()
    report["checks"]["backup"] = check_backup()
    report["checks"]["git"] = check_git()
    report["checks"]["disk"] = check_disk()
    report["checks"]["pending"] = check_pending()

    for name, result in report["checks"].items():
        s = result.get("status", "?")
        _log_event("check", name, {"status": s})
        log.info(f"  {name}: {'OK' if s == 'OK' else f'** {s} **'}")

    # Repairs with cooldown + verification
    repair_map = {
        "index": (lambda: report["checks"]["index"]["status"] == "STALE", repair_index),
        "kg": (lambda: report["checks"]["kg"]["status"] in ("EMPTY", "CORRUPT", "MISSING"), repair_kg),
        "backup": (lambda: report["checks"]["backup"]["status"] in ("STALE", "NEVER"), repair_backup),
        # git: check-only, no auto-repair (never auto-commit)
    }

    for comp, (should_repair, repair_fn) in repair_map.items():
        if should_repair():
            r = repair_fn(check_only)
            report["repairs"][comp] = r

            # Escalation: repair ran but verification failed
            if r["result"] not in ("skipped", "cooldown") and not r["verified"]:
                msg = f"{comp} repair completed but verification FAILED"
                report["escalations"].append(msg)
                _log_event("escalate", comp, {"reason": "verify_failed", "result": r["result"]})

            # Escalation: stuck in cooldown for too long (check if problem persists)
            if r["result"] == "cooldown":
                _log_event("skip", comp, {"reason": "cooldown_active"})

    if report["repairs"]:
        log.info("  Repairs: %s", {k: v["result"] for k, v in report["repairs"].items()})

    if report["escalations"]:
        log.info("  ESCALATIONS: %s", report["escalations"])

    # Inject dashboard
    inject_health_block(report)

    # Write status layer products
    _write_system_health(report)
    _write_recommended_actions(report)

    # Legacy log (keep backward compat)
    legacy_log = GENERATED / "health_log.jsonl"
    with open(legacy_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")

    log.info("Done.")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    result = run(check_only=args.check_only)
    if result is None:
        sys.exit(2)  # locked
    if result.get("escalations"):
        sys.exit(1)  # escalations present
    sys.exit(0)
