"""
summarize_level_v_runtime.py — Level V runtime metrics
========================================================

Reads health_event_log.jsonl, computes 24h and 7d statistics.
Outputs level_v_runtime_metrics.md.

Usage:
    python scripts/summarize_level_v_runtime.py
"""

import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENERATED = PROJECT_ROOT / "generated"
EVENT_LOG = GENERATED / "health_event_log.jsonl"
OUTPUT = GENERATED / "level_v_runtime_metrics.md"


def load_events():
    if not EVENT_LOG.exists():
        return []
    events = []
    for line in EVENT_LOG.read_text("utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def filter_window(events, hours):
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    return [e for e in events if e.get("ts", "") >= cutoff]


def count_types(events):
    counts = Counter()
    for e in events:
        t = e.get("type", "unknown")
        counts[t] += 1
    return dict(counts)


def count_by_component(events, event_type):
    counts = Counter()
    for e in events:
        if e.get("type") == event_type:
            counts[e.get("component", "?")] += 1
    return dict(counts)


def count_verify_results(events):
    passed = sum(1 for e in events if e.get("type") == "verify" and e.get("passed"))
    failed = sum(1 for e in events if e.get("type") == "verify" and not e.get("passed"))
    return passed, failed


def summarize(events, label):
    types = count_types(events)
    repairs = count_by_component(events, "repair")
    skips = count_by_component(events, "skip")
    escalations = count_by_component(events, "escalate")
    v_pass, v_fail = count_verify_results(events)

    lines = [
        f"### {label}",
        f"- Total events: {len(events)}",
        f"- Checks: {types.get('check', 0)}",
        f"- Repairs: {types.get('repair', 0)} ({repairs if repairs else 'none'})",
        f"- Verifications: pass={v_pass}, fail={v_fail}",
        f"- Escalations: {types.get('escalate', 0)} ({escalations if escalations else 'none'})",
        f"- Skips: {types.get('skip', 0)} ({skips if skips else 'none'})",
        f"- Lock events: {types.get('lock', 0)}",
        "",
    ]
    return "\n".join(lines)


def unique_runs(events):
    """Count distinct daemon runs (each run starts with a batch of 'check' events)."""
    runs = set()
    for e in events:
        if e.get("type") == "check":
            ts = e.get("ts", "")[:16]  # group by minute
            runs.add(ts)
    return len(runs)


def main():
    all_events = load_events()
    last_24h = filter_window(all_events, 24)
    last_7d = filter_window(all_events, 168)

    md = [
        "# Level V Runtime Metrics",
        "",
        f"Generated: {datetime.now().isoformat()[:19]}",
        f"Event log: {len(all_events)} total events",
        f"Daemon runs (all time): ~{unique_runs(all_events)}",
        f"Daemon runs (24h): ~{unique_runs(last_24h)}",
        f"Daemon runs (7d): ~{unique_runs(last_7d)}",
        "",
        summarize(last_24h, "Last 24 hours"),
        summarize(last_7d, "Last 7 days"),
        summarize(all_events, "All time"),
        "---",
        "",
        "## Anomaly Indicators",
        "",
    ]

    # Check for anomalies
    anomalies = []
    v_pass_7d, v_fail_7d = count_verify_results(last_7d)
    if v_fail_7d > 0:
        anomalies.append(f"- {v_fail_7d} verification failure(s) in 7d — check if repairs are actually working")
    esc_7d = sum(1 for e in last_7d if e.get("type") == "escalate")
    if esc_7d > 3:
        anomalies.append(f"- {esc_7d} escalations in 7d — possible persistent unresolved issue")
    lock_7d = sum(1 for e in last_7d if e.get("type") == "lock")
    if lock_7d > 0:
        anomalies.append(f"- {lock_7d} stale lock clearance(s) — daemon may be hanging or crashing")
    skip_cooldown_7d = sum(1 for e in last_7d if e.get("type") == "skip" and e.get("reason") == "cooldown")
    if skip_cooldown_7d > 10:
        anomalies.append(f"- {skip_cooldown_7d} cooldown skips in 7d — same issue keeps recurring but repair doesn't stick")

    if anomalies:
        md.extend(anomalies)
    else:
        md.append("No anomalies detected.")

    md.extend(["", ""])

    OUTPUT.write_text("\n".join(md), "utf-8")
    print("\n".join(md))
    print(f"\nSaved to: {OUTPUT}")


if __name__ == "__main__":
    main()
