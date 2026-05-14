# synthesis-rules.md — Final Synthesis Protocol

## Who writes the synthesis

By default, Claude (the Router) writes `50_summary.md`.

Opus writes it only when escalation is triggered. See `role-permissions.md` for the escalation threshold.

## When synthesis begins

Synthesis begins immediately after a stop condition is met (round limit, convergence, or user stop).
It does not begin after a GLM BLOCK — a BLOCK requires user decision first.

## What synthesis must contain

`50_summary.md` must contain all five sections, in this order:

### 1. Run header

```
# Synthesis — <task title>
Date: <YYYY-MM-DD>
Rounds completed: <N> / <limit>
Stop reason: <round_limit | convergence | user_stop>
Synthesizer: <claude | opus>
Artifacts consumed: <list of artifact paths>
```

### 2. Consolidated findings

Merge all reasoning artifacts (20_reasoning*.md) into a single narrative.
- Do not duplicate content — compress repeated conclusions into one statement
- Where DeepSeek challenged Qwen's output, state the challenge and the resolution
- Where GLM issued CONDITIONAL, state the condition and whether it was addressed in a later round

### 3. Risk and review summary

Derived from GLM's review artifacts (40_review*.md).
- List all CONDITIONAL items from every GLM round
- For each: state whether it was addressed by a subsequent round or remains open
- If GLM issued no review (no GLM round occurred), note this explicitly

### 4. Decision or recommendation

The actionable output of the deliberation.
- State what the team concluded, not just what each model said
- If rounds diverged or conflicted without resolution, state the unresolved tension explicitly — do not paper over it
- If the task was hypothesis stress-testing: state whether the hypothesis survived, was modified, or was rejected
- If the task was planning: state the recommended plan with flagged risks

### 5. Open items

Anything unresolved that the user should act on before proceeding:
- Open CONDITIONAL items from GLM that were not addressed
- Assumptions that were not stress-tested within the round limit
- Questions that emerged but could not be pursued before the limit

If there are no open items, write: "No open items."

## What synthesis must NOT do

- Do not invent content that no artifact supports
- Do not re-run any model or add a "bonus round" after the stop condition
- Do not call synthesis complete before all five sections are written
- Do not mark `status: done` in `50_summary.md` until the file is fully written

## Completion marker

The last line of `50_summary.md` must be:

```
status: done
```

This is the sentinel that `classify_current_task()` reads. Without it, `init_current_task.py`
will classify the run as `in_progress` and refuse to initialize a new task.

## After synthesis

1. Emit `team.synthesis.completed`
2. Emit `team.stopped` with the stop reason
3. Output the completion report to the user:

```
Team run complete.
Task: <title>
Rounds: <N>
Stop reason: <reason>
Synthesis: 50_summary.md
Open items: <count or "none">
Archive recommended: python "E:\Obsidian\scripts\archive_current_task.py"
```

4. Do not archive automatically — ask or recommend, do not execute.
