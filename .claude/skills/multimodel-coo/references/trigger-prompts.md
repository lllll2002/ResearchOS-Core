# Trigger Prompts

Use these prompts when Claude should activate `multimodel-coo` without extra setup discussion.

## Minimal

- `Use multimodel-coo for this task.`
- `Use multimodel-coo and choose the lightest sufficient mode.`

## Qwen-first

- `Use multimodel-coo in Qwen-first mode.`
- `Use multimodel-coo, let Qwen draft the task card first.`
- `Use multimodel-coo and keep Opus out unless escalation is justified.`

## With initialization

- `Use multimodel-coo and initialize current_task for this request.`
- `Use multimodel-coo, create the workflow artifacts, and then decide whether Qwen, DeepSeek, Codex, GLM, or Opus are needed.`

## Review-gated

- `Use multimodel-coo, let Qwen draft the task card, and require GLM review before Codex.`
- `Use multimodel-coo, keep implementation bounded, and require GLM review before final synthesis.`

## Architecture-heavy

- `Use multimodel-coo in full architecture mode.`
- `Use multimodel-coo, escalate to Opus because architecture design is required.`
