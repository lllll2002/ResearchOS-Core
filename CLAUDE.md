# CLAUDE.md — Claude Code Integration

> Read [AGENTS.md](AGENTS.md) first. This file adds Claude-specific enhancements.

---

## Cold-Start Sequence

| Step | File | Purpose |
|------|------|---------|
| 1 | `AGENTS.md` | System overview and agent contract |
| 2 | `CLAUDE.md` | This file — Claude-specific workflow |
| 3 | `docs/architecture/skills_map.md` | Available skills by category |

---

## Working With This Repo

### CLI-first

Always prefer CLI commands over manual file manipulation:

```bash
scholaraio search "query"      # hybrid search
scholaraio topics              # topic clustering
scholaraio benchmark           # system verification
scholaraio ws list             # list workspaces
```

### Skills

49 skills are available in `.claude/skills/`. Key categories:

- **Research core**: search, show, enrich, ingest, topics, graph, citations, index, workspace, export, import, audit
- **Writing**: paper-writing, paper-pipeline, writing-polish, review-response, citation-check, research-gap
- **Ops**: setup, metrics

See `docs/architecture/skills_map.md` for the full classification.

### Status Products

If Level V operations are running, check system state via:

- `generated/system_health.json` — current health status
- `generated/recommended_actions.json` — suggested repairs
- `generated/system_manifest.json` — full system snapshot

### Directory Conventions

| Directory | Purpose |
|-----------|---------|
| `scholaraio/` | Engine code — do not modify unless fixing bugs |
| `scripts/` | Operations and automation |
| `data/` | Papers and indexes (local, gitignored) |
| `workspace/` | Active research workspaces (local, gitignored) |
| `vault/` | User's Obsidian vault (local, gitignored) |
| `vault-template/` | Starter vault structure (committed) |
| `demo-data/` | Public test data (committed) |

---

## Safety Rules

| Rule | Detail |
|------|--------|
| Data location | All user data in local directories, not committed |
| File operations | Ask before modifying config or deleting data |
| Destructive operations | Require explicit user confirmation |
| Skill editing | Use `/skill-creator` only |
| Dependencies | Do not auto-install packages without user consent |

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `RESEARCH_OS_VAULT` | Path to Obsidian vault | `<project_root>/vault` |
| `RESEARCH_OS_BACKUP_LOG` | Backup log location | `<project_root>/backups/backup_log.txt` |
| `RESEARCH_OS_WORKFLOW` | Workflow task directory | `<project_root>/workspace/current_task` |
| `RESEARCH_OS_EVENTS` | Event log directory | `<project_root>/workspace/events` |
