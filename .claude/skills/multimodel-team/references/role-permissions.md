# role-permissions.md — Per-Model Allowed and Forbidden Actions

## Router (Claude / Claude Code)

The Router is the only entity with routing authority.

| Action | Allowed |
|---|---|
| Select next speaker | YES — sole authority |
| Decide to stop early | YES |
| Trigger Opus escalation | YES — when threshold met |
| Write synthesis | YES |
| Assign a speaker based on prior output | YES |
| Allow a model to self-delegate | NO — never |

## Qwen (qwen_reason.py — local, qwen3:8b)

Role: Initial decomposition, task breakdown, option generation, lightweight reasoning.

| Action | Allowed |
|---|---|
| Produce reasoning memo | YES |
| Write to 20_reasoning.md | YES |
| Call or mention DeepSeek | NO |
| Call or mention GLM | NO |
| Initiate a new round | NO |
| Make architecture decisions | NO |

Qwen speaks first by default when the task needs decomposition. It handles breadth,
not depth. When depth is needed, the Router escalates to DeepSeek.

## DeepSeek (deepseek_reason.py — remote API)

Role: Deep reasoning, failure-mode analysis, hypothesis stress-testing, multi-option tradeoff.

| Action | Allowed |
|---|---|
| Produce deep reasoning memo | YES |
| Write to 20_reasoning.md | YES |
| Challenge prior Qwen output | YES — when Router assigns it to do so |
| Call or mention Codex | NO |
| Approve execution plans | NO |
| Initiate a new round | NO |

DeepSeek is called when the task requires reasoning depth that Qwen cannot provide,
or when the Router wants a prior output stress-tested.

## GLM (glm_review.py — remote API)

Role: Review, risk audit, blocking, recommendation. GLM is a gate, not an actor.

| Action | Allowed |
|---|---|
| Issue PASS verdict | YES |
| Issue BLOCK verdict | YES — stops the run |
| Issue CONDITIONAL verdict with recommendations | YES |
| Write to 40_review.md | YES |
| Assign the next speaker | NO |
| Approve Codex execution independently | NO |
| Initiate a new round | NO |
| Run code or produce implementation | NO |

A GLM BLOCK verdict is a hard stop. Claude must report it to the user and
present the blocking issues before any further action. The user decides whether
to fix and retry or abandon.

## Codex (bridge_runner.py → codex.cmd)

Role: Code execution, file operations, batch processing. Execution only.

| Action | Allowed |
|---|---|
| Write files within allowed_write_paths | YES |
| Create result card | YES |
| Execute the task as instructed | YES |
| Initiate a new round | NO |
| Decide to run additional steps beyond the task card | NO |
| Write to current_task stage files directly | NO — bridge result goes to 30_implementation.md via Claude |

After Codex completes, Claude writes the implementation record to 30_implementation.md.
Codex itself does not write to stage files.

## Opus (Claude Opus model)

Role: High-quality synthesis, architecture decisions, cross-module reasoning.
Opus is NOT the default synthesizer. Claude (Sonnet) handles synthesis unless escalated.

### Escalation threshold — Opus only enters when at least one is true:

- The task involves cross-module or system-level architecture decisions
- Multiple rounds produced conflicting outputs that require expert arbitration
- The synthesis requires long-horizon reasoning the Router cannot perform in Sonnet
- The user explicitly requests Opus

### Escalation procedure:

1. Router emits `team.escalation` event
2. Router tells the user: "Opus escalation triggered — reason: <reason>"
3. User confirms or overrides
4. Opus writes `50_summary.md` instead of Claude

Opus does not participate in individual rounds. It only enters at synthesis.
