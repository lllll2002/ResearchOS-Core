# event-format.md — Team Mode Event Schema

## Event file location

Team mode events go to the same directory as bridge events:
```
E:\Obsidian\.ai-bridge\events\team-<task-slug>-<stamp>.jsonl
```

Example: `team-hypothesis-stress-test-20260404-120000.jsonl`

Claude creates this file at the start of Step 3 (after confirmation) and appends to it
throughout the run. One record per line, UTF-8, LF line endings.

## Base record shape

Every record has:
```json
{
  "ts": "2026-04-04T12:00:00",
  "type": "<event-type>",
  ... event-specific fields
}
```

## Event types

### team.started
Emitted once when the run begins, after user confirmation.
```json
{
  "ts": "...",
  "type": "team.started",
  "task": "<task title>",
  "round_limit": 3,
  "team": ["qwen", "deepseek", "glm"],
  "event_file": "<path to this file>"
}
```

### team.round.assigned
Emitted when Router selects the next speaker.
```json
{
  "ts": "...",
  "type": "team.round.assigned",
  "round": 1,
  "speaker": "qwen",
  "router_reasoning": "Qwen assigned for initial decomposition before stress-test.",
  "artifact_target": "E:\\Obsidian\\01_Planning\\workflows\\current_task\\20_reasoning.md"
}
```

### team.round.completed
Emitted after artifact is written and Router has reviewed it.
```json
{
  "ts": "...",
  "type": "team.round.completed",
  "round": 1,
  "speaker": "qwen",
  "artifact_path": "E:\\Obsidian\\01_Planning\\workflows\\current_task\\20_reasoning.md",
  "router_decision": "continue",
  "next_speaker": "deepseek"
}
```
`router_decision` is one of: `continue`, `stop_convergence`, `stop_limit`, `stop_block`, `stop_user`, `escalate_opus`

### team.round.failed
Emitted when a round produces no valid artifact.
```json
{
  "ts": "...",
  "type": "team.round.failed",
  "round": 1,
  "speaker": "qwen",
  "reason": "Wrapper returned error: HTTP 502"
}
```

### team.escalation
Emitted if Opus escalation threshold is triggered.
```json
{
  "ts": "...",
  "type": "team.escalation",
  "triggered_at_round": 2,
  "reason": "Architecture decision requires Opus-level synthesis"
}
```

### team.synthesis.started
```json
{
  "ts": "...",
  "type": "team.synthesis.started",
  "synthesizer": "claude",
  "rounds_completed": 2,
  "artifacts": ["20_reasoning.md", "40_review.md"]
}
```

### team.synthesis.completed
```json
{
  "ts": "...",
  "type": "team.synthesis.completed",
  "synthesizer": "claude",
  "artifact": "50_summary.md"
}
```

### team.stopped
Emitted when the run ends for any reason.
```json
{
  "ts": "...",
  "type": "team.stopped",
  "reason": "round_limit",
  "rounds_completed": 3,
  "valid_rounds": 3
}
```

## Snapshot compatibility

These events are written to the same `events/` directory that `bridge_event_snapshot.py` reads.
The snapshot script will load them, but they do not match any existing event-type handler,
so they will appear as phantom items (empty timeline) in the live panel.

This is acceptable for now. Team events are primarily for audit and post-run review,
not live dashboard display.
