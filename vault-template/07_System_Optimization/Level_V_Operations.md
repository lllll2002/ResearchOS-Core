# Level V Operations

Automated health monitoring and self-repair for the Research OS.

## Components

| Component | Script | Purpose |
|-----------|--------|---------|
| Health Daemon | `scripts/health_daemon.py` | Periodic system health checks |
| Scheduler | `scripts/run_health_daemon.ps1` | PowerShell wrapper for daemon |
| Task Registration | `scripts/register_health_daemon_tasks.ps1` | Windows Task Scheduler setup |
| Manifest Generator | `scripts/generate_system_manifest.py` | System state snapshot |
| Frontmatter Lint | `scripts/lint_frontmatter.py` | Metadata quality checks |
| Runtime Summary | `scripts/summarize_level_v_runtime.py` | Operational statistics |

## Status Products

The daemon generates three files in `generated/`:

1. `system_manifest.json` — full system state
2. `system_health.json` — health check results
3. `recommended_actions.json` — suggested repairs

## Schedule

| Time | Action |
|------|--------|
| Startup | Full health check |
| 07:30 | Morning check |
| 23:30 | Nightly check |

## Setup

```powershell
# Manual run
powershell -ExecutionPolicy Bypass -File scripts/run_health_daemon.ps1

# Register as scheduled task (requires Administrator)
powershell -ExecutionPolicy Bypass -File scripts/register_health_daemon_tasks.ps1
```
