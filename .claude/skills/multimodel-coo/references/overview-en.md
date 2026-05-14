# multimodel-coo Overview

> One line: route complex work to the right model, keep Claude in control, and keep every important step on disk.

## What this skill does

Normally Claude handles a task directly.
When a task grows beyond a reasonable single-pass answer, `multimodel-coo` breaks it into stages and routes the work to specialist models.

| Model | Best at |
|------|---------|
| Qwen3:8b local | task decomposition, task-card drafting, template generation |
| DeepSeek | hard reasoning, failure-mode analysis, option comparison |
| Codex | code execution, scripts, batch work, file operations |
| GLM | risk audit, task-card review, implementation review |
| Claude / Opus | top-level control, escalation decisions, final synthesis |

Models do not chat freely with each other. They hand off through staged artifacts written to files.

## Trigger phrases

Examples:
- `/multimodel-coo`
- `/multimodel-coo -1`
- `/multimodel-coo -2`
- `/multimodel-coo -3`
- `/multimodel-coo -4`
- `open multi-model`
- `handle this with multiple models`
- `use multi-model`

These are user interaction triggers, not shell commands.

## The four routes

### Route -1: simple execution
`Claude -> Qwen -> Codex(optional) -> Claude`

### Route -2: risk-gated execution
`Claude -> Qwen -> GLM(task-card review) -> Codex -> GLM(implementation review) -> Claude`

### Route -3: reasoning-heavy
`Claude -> Qwen -> Claude`
or
`Claude -> DeepSeek -> Claude`

### Route -4: complex architecture
`Opus -> DeepSeek -> Codex -> GLM -> Opus`

## Typical interaction

1. User asks for multi-model handling
2. Claude runs preflight
3. Claude proposes a route and waits for confirmation
4. After confirmation, Claude runs the selected stages
5. Claude writes final summary and recommends archive or continuation

## Stage artifacts

Path:
`E:/Obsidian/01_Planning/workflows/current_task`

- `00_request.md`
- `10_plan.md`
- `20_reasoning.md`
- `30_implementation.md`
- `40_review.md`
- `50_summary.md`
- `task_board.md`

## When not to use this skill

- the task is simple enough for Claude alone
- you only need literature search
- you only need Codex to execute an already-bounded task

## Notes

- Qwen is the default cheap planner
- DeepSeek is for hard reasoning, not default routing
- Codex is execution-only and must use the bridge
- GLM acts as a review gate when needed
- Opus is reserved for architecture-heavy or synthesis-heavy work
