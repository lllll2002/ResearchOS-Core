# System Overview

Research OS is a local-first, agent-neutral research operating system.

## Architecture Layers

```
┌─────────────────────────────────────┐
│  Agent Layer (Claude, Codex, etc.)  │  ← optional
├─────────────────────────────────────┤
│  Skills (.claude/skills/)           │  ← agent-specific capabilities
├─────────────────────────────────────┤
│  CLI (scholaraio)                   │  ← core interface
├─────────────────────────────────────┤
│  Engine (scholaraio/)               │  ← indexing, search, topics, KG
├─────────────────────────────────────┤
│  Operations (scripts/)              │  ← health, manifest, scheduling
├─────────────────────────────────────┤
│  Vault (Obsidian)                   │  ← notes, planning, wiki
├─────────────────────────────────────┤
│  Data (local, gitignored)           │  ← papers, indexes, workspace
└─────────────────────────────────────┘
```

## Key Principles

- **CLI-first**: all core functionality works without any AI agent
- **Agent-enhanced**: agents are optional interfaces, not dependencies
- **Data-private**: real data stays local, never committed
- **Local-first**: no external services required for basic operation

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Engine | `scholaraio/` | Literature management core |
| Scripts | `scripts/` | Operations and automation |
| Skills | `.claude/skills/` | Agent skill definitions |
| Vault Template | `vault-template/` | Obsidian starter structure |
| Demo Data | `demo-data/` | Public test data |
| Docs | `docs/` | Architecture and setup guides |
