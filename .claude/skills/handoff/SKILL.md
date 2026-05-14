---
name: handoff
description: Save current task execution state to a handoff card for fast context recovery. Trigger when user says "park this", "switch to", "save progress", or runs /handoff directly.
argument-hint: "[project name (optional, auto-detected)]"
allowed-tools: Read, Write, Edit, Glob
---

# Task Handoff Card Writer

Write the current task's execution state to `memory/handoffs/` so the next session (or post-switch) can resume in 1 turn.

## Execution Flow

1. **Identify current task context**:
   - Read `01_Planning/AI_active_context.md` to determine the active project
   - Review operations performed in this session (files read, files modified, decisions made)
   - If the user passed a project name argument, use it; otherwise infer from active_context

2. **Check for existing active handoff card**:
   - Scan `memory/handoffs/*.md` (exclude archive/)
   - Match by `project` field in frontmatter (not by filename or free-text task description)
   - If a card exists with matching project and status: interrupted, update it instead of creating a new one

3. **Write handoff card**:
   - Filename format: `memory/handoffs/{project}_{YYYY-MM-DD}_{short-description}.md`
   - Use the following schema:

```markdown
---
task_id: {{project}}__{{YYYY-MM-DD}}__{{seq}}  # e.g. Phase_Separation__2026-04-25__1 (seq = 1 unless multiple cards same day)
task: {{one-line description of current work}}
project: {{canonical directory name: Phase_Separation | Biocomputing_Review | Organoid_MEA_Chip | Needle_Puncture_Mechanics | Apoptosis_Tissue_Simulation | other}}
created: {{ISO timestamp}}
status: interrupted
trigger: {{source: /handoff | close-day | user-explicit | operator-detected-switch | context-compaction}}
---

## State at interruption
- **Conclusion so far**: {{conclusions established or work completed in this session}}
- **Blocked on**: {{what prevented continuation; write "voluntary_switch" if not blocked}}
- **Next step**: {{specific next action with file path or command -- must not be vague}}

## Entry points
- Primary file: {{absolute path to open first on resume}}
- Wiki page: {{relevant wiki page path, omit if none}}
- Script/command: {{command to run, omit if none}}

## Context
- Files modified: {{list of files modified in this session}}
- Key decisions made: {{important decisions made in this session}}
```

4. **Confirm output**:
   - Tell the user the handoff card was written, give the file path
   - Summarize what was saved in one sentence
   - Do not repeat the full card content

## Rules

- **Next step must be specific**: reject vague descriptions like "continue writing the paper"; require specifics like "open manuscript.md, start S1.2 paragraph 3 with 3 pieces of organoid computing evidence"
- **Do not auto-update AI_active_context.md**: handoff cards are independent L4 state, do not interfere with L1 router
- **One active card per project**: new card replaces old one (old card moves to archive/)

## Lifecycle

See `01_Planning/lifecycle_rules.md` section 1 for full handoff state machine, transitions, and constraints.
