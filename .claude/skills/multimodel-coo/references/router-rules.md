# Router Rules

Use this file to decide the default route before invoking any stage model.

## Default Rule

Start with Qwen3:8b unless the task is clearly architecture-heavy or high-risk.

## Route Classes

### trivial
Route:
- Human -> Qwen -> Human

Examples:
- tiny formatting tasks
- template filling
- fixed-version task cards
- simple summaries

### standard
Route:
- Human -> Qwen -> Codex(optional) -> Human

Examples:
- bounded scripts
- skill scaffolding
- standard bridge task generation
- simple file transformations

### reasoning-heavy
Route:
- Human -> Qwen or DeepSeek -> Human
- optional Opus synthesis

Examples:
- failure-mode analysis
- theory comparison
- experiment design
- cause analysis

### execution-reviewed
Route:
- Human -> Qwen -> Codex -> GLM -> Human

Examples:
- code changes with user-visible impact
- nontrivial skill updates
- task cards with meaningful risk

### architecture-heavy
Route:
- Human -> Opus -> DeepSeek -> Codex -> GLM -> Opus -> Human

Examples:
- software architecture design
- cross-module refactor strategy
- long-cycle research planning
- high-stakes synthesis

## Versioned Task Cards

Generating a task card in a specified format or version is a Qwen-first job.
Use Qwen first for:
- schema-constrained task cards
- fixed frontmatter layout
- version-to-version conversion
- standard execution card drafting

Do not escalate versioned task-card generation to Opus unless the task also includes architecture-heavy decisions.

## GLM Task-Card Review Gate

Ask GLM to review a task card when any of the following is true:
- allowed_write_paths look wide
- rollback is weak or missing
- acceptance criteria are unclear
- the task combines multiple unrelated goals
- the task could trigger broad file changes

GLM should review for:
- scope creep
- rollback quality
- acceptance quality
- missing blockers
- missing edge cases
