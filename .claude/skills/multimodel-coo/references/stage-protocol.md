# Stage Protocol

## Required Order

1. initialize `current_task` if missing
2. write `00_request.md`
3. write `10_plan.md`
4. optional `20_reasoning.md`
5. optional bridge task for Codex execution
6. optional `30_implementation.md`
7. optional `40_review.md`
8. write `50_summary.md`
9. decide archive recommendation

## Qwen Stage

Purpose:
- first-pass routing
- cheap decomposition
- versioned task-card generation
- standard task-card drafting
- lightweight reasoning

Default:
- use Qwen first for trivial and standard work

## DeepSeek Stage

Purpose:
- problem decomposition for hard cases
- assumptions
- edge cases
- failure modes
- recommended route
- rejected routes

Do not use DeepSeek to edit project files directly.

## Codex Stage

Purpose:
- code changes
- scripts
- file transforms
- skill creation
- bounded batch execution

Always use a bridge task and respect `allowed_write_paths`.

## GLM Stage

Purpose:
- task-card review
- bug/risk review
- missing tests
- missing controls
- overclaim detection
- consistency checks between plan, reasoning, and implementation

Use GLM before Codex when a task card looks risky.
Do not use GLM as the primary planner or implementer.

## Opus Stage

Purpose:
- architecture-heavy planning
- cross-module strategy
- long-horizon research planning
- final synthesis after complex work

Do not invoke Opus unless the escalation threshold is met.
