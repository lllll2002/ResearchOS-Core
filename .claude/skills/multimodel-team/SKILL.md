---
name: multimodel-team
description: >
  Advanced round-based multi-model team mode for E:\Obsidian. Use this skill — not multimodel-coo —
  when a task genuinely requires models to build on each other's outputs across multiple structured rounds,
  such as: hypothesis stress-testing, adversarial review, multi-angle architecture debate, or iterative
  refinement where the next speaker depends on what the previous round produced.
  Trigger phrases: /multimodel-team, use team mode, open team mode, team debate, multi-model team.
  DO NOT trigger for ordinary planning or execution tasks — those belong to multimodel-coo.
  This skill is ONLY for tasks where round-based deliberation adds real value over a linear pipeline.
  For publication-grade literature review workflows, use the separate skill
  `multimodel-team-reviewer`.
---

# multimodel-team

Advanced opt-in skill. Claude is the Router and the only entity that decides the next speaker each round.
No model may self-delegate, call another model, or initiate a new round.

Boundary: if the user wants a formal review, related work section, comprehensive literature audit,
corpus screening, DOI map, or evidence matrix, use `multimodel-team-reviewer` instead of this skill.

Read `references/team-mode.md` now if you need full design context.

---

## Step 0 — Preflight

```bash
python "E:/Obsidian/scripts/multimodel_preflight.py"
```

Also check `current_task` state:
```bash
python "E:/Obsidian/scripts/init_current_task.py" --title "placeholder" --check
```

If state is `in_progress` or `completed`: tell the user, ask whether to archive or force. Do not proceed silently.

---

## Step 1 — Task Analysis and Team Composition

Before proposing a team, analyze:

1. What is the core question or problem?
2. Which models add non-redundant value here? Only include models that contribute something the others cannot.
3. How many rounds are needed? Start with 2. Justify any proposal above 3.
4. What artifact does each round produce?

Consult `references/role-permissions.md` for what each model is and is not allowed to do.

---

## Step 2 — Proposal Card

Present to the user before any execution:

```
== multimodel-team proposal ==

Task: <one-sentence description>

Proposed team:
  Round 1: <Speaker> — <purpose> → artifact: <stage file>
  Round 2: <Speaker> — <purpose> → artifact: <stage file>
  Round 3 (if needed): <Speaker> — <purpose> → artifact: <stage file>
  Synthesis: Claude/Opus — final output → 50_summary.md

Round limit: <N> (hard stop)

Stop conditions:
  - Round limit reached
  - GLM issues BLOCK verdict
  - No new information produced
  - You say stop

Environment:
  Qwen: <OK / unavailable>
  DeepSeek: <OK / unavailable>
  GLM: <OK / unavailable>
  Codex: <OK / available>

Confirm this team, or adjust:
  - change a speaker
  - reduce rounds
  - skip a role
```

Wait for explicit confirmation before any execution.

---

## Step 3 — Initialize

After confirmation:

```bash
python "E:/Obsidian/scripts/init_current_task.py" --title "<task-title>" [--force if approved]
```

Write the full task description into `00_request.md`.

---

## Step 4 — Execute Rounds

For each round:

1. **Router decides speaker** — based on task state and prior round output.
2. **Call the designated model** — pass `--round`, `--round-speaker`, `--round-reasoning`, and
   `--round-prior-artifacts` to the wrapper. The wrapper writes the round header directly into
   the artifact at write time. No post-call patching is needed.
3. **Validate the artifact** — file must exist, be non-empty, and contain the round header.
   If any check fails: emit `team.round.failed`, do NOT count toward round limit, report to user,
   ask: retry, skip, or stop. Do not proceed until resolved (see `references/stop-rules.md` §2).
4. **Log the round event** — append `team.round.assigned` (before) and `team.round.completed`
   (after) to the event file (see `references/event-format.md`).
5. **Router reviews the output** — decide: continue to next round, trigger stop condition, or escalate.

Round speaker → wrapper mapping (with `--round` args):
```
Qwen      → python "E:/Obsidian/scripts/ai_wrappers/qwen_reason.py"
              --round N --round-speaker "qwen3:8b"
              --round-reasoning "<one sentence>" --round-prior-artifacts "<list or none>"
              → 20_reasoning.md

DeepSeek  → python "E:/Obsidian/scripts/ai_wrappers/deepseek_reason.py"
              --round N --round-speaker "deepseek-reasoner"
              --round-reasoning "<one sentence>" --round-prior-artifacts "<list or none>"
              → 20_reasoning.md

GLM       → python "E:/Obsidian/scripts/ai_wrappers/glm_review.py"      → 40_review.md
              (GLM does not yet support --round-header; Router patches manually if needed)

Codex     → python "E:/Obsidian/scripts/bridge_runner.py" --task <path> → 30_implementation.md
              (Codex does not use --round-header)
```

If the same stage file is used across rounds, name the artifact with a round suffix
(e.g. `20_reasoning_r2.md`) and copy the final version back as the canonical file before synthesis.

Report after each round completes:
```
[Round N complete] Speaker: <model> | Artifact: <path> | Router decision: <continue / stop / escalate>
```

**Hard rules:**
- Qwen cannot call DeepSeek. DeepSeek cannot call Codex. No model self-delegates.
- GLM can only review, block, or recommend. GLM cannot approve execution or assign the next speaker.
- Codex cannot initiate or continue rounds. Codex only executes what the Router assigns.
- Opus only enters if the escalation threshold in `references/role-permissions.md` is met.
- Round limit is a hard ceiling. When it is reached, proceed immediately to synthesis.

---

## Step 5 — Synthesis

Follow `references/synthesis-rules.md` exactly for the required sections and completion marker.

Key constraints:
- `50_summary.md` must end with `status: done` — this is the sentinel read by `init_current_task.py`
- If Opus escalation was triggered, Opus writes `50_summary.md` instead of Claude
- Do not start synthesis after a GLM BLOCK — wait for user decision first
- Emit `team.synthesis.started` before writing, `team.synthesis.completed` after

---

## Step 6 — Completion Report

```
== multimodel-team completed ==

Rounds executed: N / limit N
Stop reason: <round limit | GLM block | convergence | user stop>
Artifacts:
  - 00_request.md
  - 10_plan.md (if written)
  - 20_reasoning.md (+ round variants)
  - 40_review.md (if GLM ran)
  - 30_implementation.md (if Codex ran)
  - 50_summary.md
  - team-<task-slug>-<stamp>.jsonl

Archive recommended. / Do not archive yet.
```

---

## References

Read as needed:
- `references/team-mode.md` — design rationale and when to use
- `references/round-protocol.md` — round mechanics and artifact rules
- `references/event-format.md` — JSONL event schema
- `references/role-permissions.md` — per-model allowed/forbidden actions
- `references/stop-rules.md` — stop condition logic
- `references/synthesis-rules.md` — final synthesis requirements
- `references/gap-c-glm-block-policy.md` — GLM BLOCK confirmation policy decision note
