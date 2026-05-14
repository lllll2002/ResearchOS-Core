# Usage Guide

## Typical trigger phrases

- `/multimodel-coo`
- `打开多模型`
- `多模型处理这个`
- `use multi-model`
- `Use multimodel-coo for this task.`
- `Use multimodel-coo, Qwen-first.`
- `Use multimodel-coo with GLM review before Codex.`

## Mode selection quick reference

| Say this | Gets you |
|----------|---------|
| `/multimodel-coo -1` | Claude → Qwen → Codex(opt) → Claude |
| `/multimodel-coo -2` | Claude → Qwen → GLM → Codex → GLM → Claude |
| `/multimodel-coo -3` | Claude → Qwen/DeepSeek → Claude |
| `/multimodel-coo -4` | Opus → DeepSeek → Codex → GLM → Opus |
| `/multimodel-coo` (no flag) | Claude proposes best fit, you confirm |

## Workflow commands

Initialize task artifacts:
```bash
python "E:/Obsidian/scripts/init_current_task.py" --title "<task title>"
```

Run Qwen reasoning:
```bash
python "E:/Obsidian/scripts/ai_wrappers/qwen_reason.py"
```

Run DeepSeek reasoning:
```bash
python "E:/Obsidian/scripts/ai_wrappers/deepseek_reason.py"
```

Run GLM review:
```bash
python "E:/Obsidian/scripts/ai_wrappers/glm_review.py"
```

Run Codex via bridge:
```bash
python "E:/Obsidian/scripts/bridge_runner.py" --task "<task_card_path>"
```

Check workflow status:
```bash
python "E:/Obsidian/scripts/workflow_status.py"
```

Archive completed task:
```bash
python "E:/Obsidian/scripts/archive_current_task.py"
```

Archive and clear:
```bash
python "E:/Obsidian/scripts/archive_current_task.py" --clear-current
```

## Stage file locations

```
E:/Obsidian/01_Planning/workflows/current_task/
├── 00_request.md
├── 10_plan.md
├── 20_reasoning.md
├── 30_implementation.md
├── 40_review.md
├── 50_summary.md
└── task_board.md
```

## Archive recommendation states

At the end of every task, Claude states one of:
- `Archive recommended.`
- `Archive recommended after one final check.`
- `Do not archive yet.`
