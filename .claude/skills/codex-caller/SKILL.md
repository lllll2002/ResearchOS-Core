---
name: codex-caller
description: >
  Orchestrate the Claude to Codex bridge workflow inside E:\Obsidian. Use this skill when Claude should generate a bridge task card, trigger bridge_runner.py, wait for Codex to finish, and then report results back to the user.
trigger_on:
  - use codex-caller
  - hand this to codex
  - give this to codex
  - create a bridge task for codex
  - run through bridge_runner
  - 使用 codex-caller
  - 交给 codex
  - codex 帮我
  - 把这个任务交给 codex
---

# codex-caller: Claude -> Codex Bridge Orchestrator

## 适用范围
当任务满足以下条件时，使用本 skill：
- 批量执行或批量重构
- Skill 创建或更新
- 代码实现、文档整理、结构化审计
- 规则明确、边界清晰、写入范围可控

不适合交给 Codex 的情况：
- 目标模糊，范围不清
- 写入边界不明确
- 高风险且尚未拆分的批量修改

## 路径约定
- 任务卡模板：`E:\Obsidian\.ai-bridge\tasks\TASK_TEMPLATE.md`
- 任务卡目录：`E:\Obsidian\.ai-bridge\tasks\`
- 结果卡目录：`E:\Obsidian\.ai-bridge\results\`
- 事件流目录：`E:\Obsidian\.ai-bridge\events\`
- 任务管理脚本：`E:\Obsidian\scripts\ai_bridge.py`
- 执行脚本：`E:\Obsidian\scripts\bridge_runner.py`
- 事件快照脚本：`E:\Obsidian\scripts\bridge_event_snapshot.py`
- 实时面板：`E:\Obsidian\workspace\bridge-live.html`
- 调试日志目录：`G:\CodexTemp\`

## UTF-8 only 规则
- 中文正式产物只以 UTF-8 文件为准。
- 终端输出、stderr、stdout、console transcript 只作为调试信息，不作为正式来源。
- 如果要把模型输出写入正式文档，必须让脚本或模型直接写文件，不要从控制台回显中反抄。
- 任务卡、结果卡、事件流、快照文件统一使用 UTF-8 编码和 `\n` 换行。
- 调试日志允许保留乱码替换字符，但必须明确标注为 debug-only。

## 标准工作流
1. 理解任务，判断是否适合交给 Codex。
2. 必要时先拆 audit 卡，再拆 execution 卡。
3. 创建任务卡并补全 frontmatter。
4. 执行 dry-run：
   `python E:\Obsidian\scripts\bridge_runner.py --task "<path>" --dry-run`
5. 正式执行：
   `python E:\Obsidian\scripts\bridge_runner.py --task "<absolute_path>"`
6. 检查结果卡、产物、事件流、调试日志。
7. 向用户汇报任务卡、结果卡、事件文件、日志文件路径。

## 任务卡要求
每张任务卡只做一件事，并完整填写这些 frontmatter 字段：
```yaml
---
id: TASK-NNN
owner: codex
status: pending
created: YYYY-MM-DD
deadline: ~
scope: <精确范围>
inputs:
  - <读取路径>
allowed_write_paths:
  - <严格的写入路径>
expected_output:
  - <具体产物>
rollback: <失败时如何恢复>
notes: <边界、限制、风格要求>
---
```

自动获取下一个任务 ID：
```bash
python E:\Obsidian\scripts\ai_bridge.py create-task --owner codex --title "<title>"
```

## Runner 调用说明
```bash
python E:\Obsidian\scripts\bridge_runner.py --task "<absolute_path>" --dry-run
python E:\Obsidian\scripts\bridge_runner.py --task "<absolute_path>"
```

Runner 内部调用：
```text
codex.cmd exec --skip-git-repo-check -s danger-full-access -
```

消息通过 stdin 传入。正式产物必须写回文件，不能依赖控制台输出。

## 事件与日志
- `runner.received`：runner 收到任务
- `task.snapshot`：任务卡快照
- `task.status`：任务状态变化
- `codex.started`：Codex 开始执行
- `codex.debug.stdout` / `codex.debug.stderr`：调试输出，不是正式产物
- `codex.completed`：Codex 返回码
- `formal.output.validated`：结果卡已按 UTF-8 通过校验
- `runner.completed` / `runner.failed` / `runner.error`：执行结论

## 执行后必须汇报
- 任务卡路径
- 结果卡路径
- 事件文件路径
- 日志文件路径
- 执行结果：done / blocked / error
- 下一步建议

## 参考文件
- `references/bridge-sop.md`
