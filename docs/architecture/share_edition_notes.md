# Share Edition Notes

This repository is a **share edition** — a public skeleton extracted from a live personal research vault.

## What's Included

- ScholarAIO literature engine (full source)
- Level V operational scripts
- 49 agent skills (research + general-purpose)
- Obsidian vault template
- Demo data for testing
- Agent adapter files (Claude, Codex, Cursor, Windsurf, Cline, Copilot)

## What's Excluded

- Real research data (papers, notes, manuscripts)
- Personal configuration (API keys, local paths)
- Runtime state (indexes, databases, logs)
- Private planning documents
- Backup and sync configurations

## Relationship to a Live System

A live Research OS has two parts:

```
research-os-core/       ← this repo (public, shareable)
research-os-private/    ← your data (local, gitignored)
```

After bootstrap, the private layer is created automatically:
- `data/` — your papers and indexes
- `workspace/` — your active research workspaces
- `config.local.yaml` — your API keys and paths
- `vault/` — your Obsidian vault (from template)
