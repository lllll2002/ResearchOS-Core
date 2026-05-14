# Model Boundaries

## Opus / Claude
- control plane
- escalation-only planner
- architecture decisions
- prioritization for complex work
- final synthesis
- memory updates

Do not use Opus as the default planner for trivial or standard tasks.

## Qwen3:8b local
- default planner
- cheap local decomposition
- first-pass routing draft
- task-card drafting
- versioned task-card generation
- lightweight challenger reasoning

Do not use Qwen as the final authority on architecture-heavy decisions.

## DeepSeek
- difficult reasoning memo
- assumptions
- edge cases
- failure modes
- option comparison for hard problems

Do not use DeepSeek as the default planner or implementer.

## OpenAI / Codex
- implementation and execution only
- use the existing bridge
- bounded code, scripts, skill creation, file transforms

## GLM
- review and audit
- task-card review
- blocking issue detection
- consistency checks between plan, reasoning, and implementation
- acceptance / rollback quality review

Do not use GLM as the primary planner or implementer.

## Configuration Rule
All model IDs, provider URLs, and API key env var names live in:
`E:\Obsidian\scriptsi_wrappers\multimodel_config.json`

Change that file when you want to swap model versions, stage defaults, or provider endpoints later.
