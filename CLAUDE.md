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
scholaraio usearch "query"     # unified hybrid search (default)
scholaraio ask "question"      # smart Q&A (auto-routes to search/SQL/KG)
scholaraio nlsearch "natural language query"  # text-to-SQL
scholaraio topics              # topic clustering
scholaraio benchmark           # system verification
scholaraio ws list             # list workspaces
scholaraio kg build            # knowledge graph
```

### Skills

Skills live in `.claude/skills/`. Each has a `SKILL.md` with trigger conditions.
Use `/skill-creator` to create or modify skills — never hand-edit.

### Memory System

Two-tier distributed memory:
- **Vault level** → `memory/` (user profile, workflow, tools)
- **Project level** → `<project>/memory/` (experiment, hardware, literature decisions)

Rules: read `MEMORY.md` before creating; frontmatter required; update index after writing.

### Reflection Rule

After completing a multi-step task (≥5 tool calls), pause and verify:
1. Did the output match the user's intent?
2. Any side effects on other files?
3. Anything that should be logged to process notes or memory?

On user "reflect" → full session audit.

**Context rot guard:** If session exceeds ~50 tool calls or spans multiple projects, suggest handoff + new session.

### Write Rules

| Event | Write target |
|-------|-------------|
| Key literature conclusion | 3 sentences: What / How / So what |
| Major decision | `process_notes.md` |
| New task generated | Project `memory/next_actions.md` |
| Session ends | Update `AI_active_context.md` |

### Safety

- All files on local drive, not cloud
- Ask before modifying or deleting
- Destructive operations need explicit confirmation (archive, never silent delete)
- `python -c` single-line only; no inline comments
- Helper models read-first; high-risk writes need approval

### Level V Operations

Health daemon runs at startup/07:30/23:30 (auto-repairs index/KG/backup):
```bash
python scripts/health_daemon.py              # full check + repair
python scripts/health_daemon.py --check-only # report only
```

Morning setup auto-generates daily plan:
```bash
python scripts/run_morning_setup.py          # generate today.md
```

Memory search across all memory files:
```bash
python scripts/memory_search.py "query"      # BM25 keyword search
python scripts/memory_search.py "query" --verbose  # with snippets
```
