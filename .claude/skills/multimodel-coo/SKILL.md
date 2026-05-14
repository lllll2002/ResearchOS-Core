---
name: multimodel-coo
description: >
  Route tasks through the installed multi-model workflow in E:\Obsidian. Trigger when the user asks for multi-model handling, mentions Qwen, DeepSeek, GLM, or Codex, or when a task needs staged planning, execution, and review. Claude remains the control plane.
---

# multimodel-coo

Use this skill when Claude should route a task through the installed multi-model system instead of handling everything in one pass.

## Runtime Goal

Claude remains the control plane.
This skill should:
1. run preflight
2. propose a route
3. wait for user confirmation
4. execute the confirmed route
5. write durable artifacts
6. recommend archive or continuation at the end

## Default Routing Rule

Use Qwen first by default.
Escalate to DeepSeek, Codex, GLM, or Opus only when task complexity or risk justifies it.

## Route Modes

### Mode -1
`Claude -> Qwen -> Codex(optional) -> Claude`

Use for:
- simple execution
- template generation
- bounded batch work
- small code tasks
- straightforward file transforms

### Mode -2
`Claude -> Qwen -> GLM(task-card review) -> Codex -> GLM(implementation review) -> Claude`

Use for:
- broad write scope
- risky file changes
- weak rollback
- changes that need review gates

### Mode -3
`Claude -> Qwen -> Claude`
or
`Claude -> DeepSeek -> Claude`

Use for:
- reasoning-heavy work
- hypothesis checks
- failure-mode analysis
- option comparison without execution

### Mode -4
`Opus -> DeepSeek -> Codex -> GLM -> Opus`

Use only when the Opus escalation threshold is met.

## Opus Escalation Threshold

Escalate to Opus only when at least one of the following is true:
- software architecture design is required
- a cross-module refactor strategy is required
- long-horizon research planning is required
- multiple approaches need real tradeoff analysis
- final high-quality synthesis is required

## Required Preflight

Before proposing any route, run:

```bash
python "E:/Obsidian/scripts/multimodel_preflight.py"
```

Preflight is the only allowed script execution before user confirmation.
Do not run wrappers or bridge execution before the user confirms a route.

## Confirmation Rule

Before execution, Claude must:
1. analyze the task
2. recommend a route
3. list available routes
4. show environment readiness
5. wait for explicit user confirmation

## current_task Initialization Discipline

Before initializing, always check the state of the existing `current_task`:

```bash
python "E:/Obsidian/scripts/init_current_task.py" --title "placeholder" --check
```

States and required actions:

| State | Meaning | Action |
|---|---|---|
| `empty` or `fresh` | Clean — safe to init | Run init normally |
| `in_progress` | Previous task still live | Ask user: archive or force? |
| `completed` | Previous task done, not archived | Archive first, then init |

**Rule**: never run `--force` silently. If state is `in_progress` or `completed`, tell the user what was found and ask for explicit confirmation before overwriting.

Archive command:
```bash
python "E:/Obsidian/scripts/archive_current_task.py"
```

Init (only after state is confirmed clean or user approves force):
```bash
python "E:/Obsidian/scripts/init_current_task.py" --title "<task title>"
# or with explicit force if user approved:
python "E:/Obsidian/scripts/init_current_task.py" --title "<task title>" --force
```

## Execution Rule

After user confirmation:
- check `current_task` state before initializing (see discipline above)
- initialize `current_task` with a title
- **create a pipeline session immediately after init** — run `create_pipeline_session.py`, read the printed `session_id` from stdout, and keep it in context for the rest of this pipeline
- pass `--session-id <session_id>` to every wrapper call (Qwen, DeepSeek, GLM) and to `bridge_runner.py` in this pipeline — this links all child runs into one grouped entry in Bridge Live v2
- call wrappers with `python`
- use `bridge_runner.py` for Codex
- write outputs to stage files, not stdout summaries
- stop immediately on failure and report the cause

## Stage Files

Artifacts live under:
`E:/Obsidian/01_Planning/workflows/current_task`

Expected files:
- `00_request.md`
- `10_plan.md`
- `20_reasoning.md`
- `30_implementation.md`
- `40_review.md`
- `50_summary.md`
- `task_board.md`

## Required Commands

Initialize workflow:
```bash
python "E:/Obsidian/scripts/init_current_task.py" --title "<task title>"
```

Create pipeline session (run once after init, before any wrappers):
```bash
python "E:/Obsidian/scripts/create_pipeline_session.py" --title "<task title>" --route "<-1|-2|-3|-4>"
```
Read the printed `session_id` from stdout (format: `coo-YYYYMMDD-HHMMSS`) and use it in all subsequent commands below.

Qwen reasoning:
```bash
python "E:/Obsidian/scripts/ai_wrappers/qwen_reason.py" --session-id <session_id>
```

DeepSeek reasoning:
```bash
python "E:/Obsidian/scripts/ai_wrappers/deepseek_reason.py" --session-id <session_id>
```

GLM review:
```bash
python "E:/Obsidian/scripts/ai_wrappers/glm_review.py" --session-id <session_id>
```

Codex execution:
```bash
python "E:/Obsidian/scripts/bridge_runner.py" --task "<task_card_path>" --session-id <session_id>
```

Archive:
```bash
python "E:/Obsidian/scripts/archive_current_task.py"
```

## Constraints

- Codex must go through `bridge_runner.py`
- use `python`, not `python3`
- wrappers read stage files by default
- user confirmation is required before wrapper or bridge execution
- `50_summary.md` must reflect the final state before archive is recommended

## References

Read as needed:
- `references/overview-en.md`
- `references/router-rules.md`
- `references/stage-protocol.md`
- `references/model-boundaries.md`
- `references/usage-guide.md`
- `references/trigger-prompts.md`
- `references/completion-criteria.md`
