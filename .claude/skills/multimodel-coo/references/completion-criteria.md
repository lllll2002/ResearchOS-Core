# Completion Criteria

Use these rules to decide whether `current_task` should be archived.

## Mark the task complete when

- the requested output has been produced, or
- the bounded execution task has been completed and summarized, or
- the task has reached a stable blocked state with a clear reason and next step.

## Required artifacts before archive

At minimum:

- `00_request.md` reflects the actual request
- `10_plan.md` reflects the executed path
- `50_summary.md` contains:
  - outcome
  - risks
  - next actions

If a stage was used, its artifact should be present and non-empty:

- reasoning used -> `20_reasoning.md`
- implementation used -> `30_implementation.md`
- review used -> `40_review.md`

## Auto-archive conditions

Claude may archive automatically when all of the following are true:

1. The task is no longer actively being worked.
2. The final answer has already been delivered to the user.
3. `50_summary.md` has been updated to match the final state.
4. There is no pending bridge task still marked `pending` or `in_progress` for the same work item.

## Archive suggestion output

When the criteria are met, Claude should say so explicitly instead of silently assuming archive:

- `Archive recommended.` when the task is complete and stable
- `Archive recommended after one final review.` when only a final human check is missing
- `Do not archive yet.` when active work remains

## Do not archive yet when

- the user is still iterating on the same task in the same work session
- Codex execution is still running
- GLM review has been requested but not written yet
- the task is blocked but the block reason has not been summarized
- the artifacts are placeholders only

## Recommended end states

### Success

- `50_summary.md` records the completed outcome
- archive `current_task`
- optionally clear `current_task` after archive

### Blocked

- `50_summary.md` records:
  - what was attempted
  - why it stopped
  - what should be retried next
- archive `current_task`
- do not clear current files if immediate retry is likely

### Continuing session

- keep `current_task` active
- update `task_board.md`
- do not archive
