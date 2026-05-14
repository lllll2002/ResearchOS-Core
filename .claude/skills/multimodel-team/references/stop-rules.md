# stop-rules.md — Stop Condition Logic

## Stop conditions (evaluated after every completed round)

Stop conditions are evaluated in priority order. The first condition that is true ends the run.

### 1. GLM BLOCK (highest priority)

Condition: GLM issued a verdict of BLOCK or BLOCKED in its review output.

Action:
- Emit `team.stopped` with `reason: glm_block`
- Report to user: the blocking issues GLM raised
- Do NOT proceed to synthesis automatically
- Ask user: fix and retry, or abandon?

### 2. Artifact failure (pause before synthesis)

Condition: A round produced no valid artifact (model error, empty output, wrapper failure).

This condition is evaluated before round limit and convergence because a corrupted
or missing artifact must be resolved before it can propagate into synthesis.

Action:
- Emit `team.round.failed`
- Do NOT count the failed round toward the round limit
- Report failure to user
- Ask: retry this round, skip and continue, or stop?

This is not an automatic stop — it requires user guidance. But it must be handled
before the Router evaluates whether to continue, stop for limit, or detect convergence.

### 3. Round limit reached

Condition: Completed valid rounds == round limit (default 3).

Action:
- Emit `team.stopped` with `reason: round_limit`
- Proceed immediately to synthesis with available artifacts
- Note in summary: "Round limit reached — synthesis based on N rounds"

### 4. Convergence detected

Condition: The Router determines the last round produced no new information or perspective
compared to the previous round. This is a judgment call by the Router, not an automatic check.

Signals of convergence:
- The speaker repeated conclusions already present in a prior artifact
- No open questions remain unaddressed
- GLM issued PASS with no non-blocking issues

Action:
- Emit `team.stopped` with `reason: convergence`
- Proceed to synthesis
- Note in summary: "Stopped at round N — convergence detected"

### 5. User stop

Condition: User says "stop", "enough", "end team mode", or similar.

Action:
- Emit `team.stopped` with `reason: user_stop`
- If any valid rounds completed, proceed to synthesis with available artifacts
- If no rounds completed, report and abandon cleanly

## What stop conditions do NOT exist

- "The model said it needs more rounds" — models cannot request more rounds
- "The task is complex" — complexity alone is not a stop condition
- Implicit continuation — if no stop condition is met and limit not reached, Router continues
- Artifact failure as lowest-priority — artifact failure (condition 2) must be resolved
  before the Router evaluates round limit or convergence, not after

## After stopping

Regardless of stop reason, if at least one valid round completed:
- Write `50_summary.md`
- Emit `team.synthesis.completed`
- Output completion report

If zero valid rounds completed (e.g. all rounds failed or user stopped at round 0):
- Write a brief `50_summary.md` noting the abandoned run
- Do not claim synthesis was performed
