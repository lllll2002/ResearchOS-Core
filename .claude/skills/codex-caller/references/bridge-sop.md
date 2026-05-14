# Claude -> Codex Bridge SOP

> 版本：2026-04-03
> 适用：E:\Obsidian 内的 Claude/Codex 文件桥接流程

---

## 一句话结论
这套桥的正式来源只能是 UTF-8 文件。
Windows、PowerShell、`codex exec`、终端回显、日志查看器之间的编码链不可靠，不能把 console transcript 当正式文档来源。

## 系统结构
```text
用户 -> Claude（判断、拆任务、生成任务卡）
     -> bridge_runner.py（校验、状态管理、调用 Codex）
     -> Codex（执行任务、直接写文件）
     -> Claude（读取 UTF-8 文件产物并汇报）
```

## 路径速查
- 任务卡目录：`E:\Obsidian\.ai-bridge\tasks\`
- 结果卡目录：`E:\Obsidian\.ai-bridge\results\`
- 事件流目录：`E:\Obsidian\.ai-bridge\events\`
- 任务卡模板：`E:\Obsidian\.ai-bridge\tasks\TASK_TEMPLATE.md`
- 结果卡模板：`E:\Obsidian\.ai-bridge\results\RESULT_TEMPLATE.md`
- 任务管理脚本：`E:\Obsidian\scripts\ai_bridge.py`
- 执行脚本：`E:\Obsidian\scripts\bridge_runner.py`
- 事件快照脚本：`E:\Obsidian\scripts\bridge_event_snapshot.py`
- 实时面板：`E:\Obsidian\workspace\bridge-live.html`
- 调试日志目录：`G:\CodexTemp\`

## UTF-8 only 规则
- 中文正式产物只以 UTF-8 文件为准。
- 终端输出只作调试用途，不作正式来源。
- stdout、stderr、console transcript、PowerShell 回显都不能反抄进正式文档。
- 如果需要把模型输出写入正式文档，必须让脚本或模型直接写文件。
- 任务卡、结果卡、事件流、快照文件统一使用 UTF-8 和 `\n`。
- 调试日志必须清楚标明 `debug-only`。

## 标准执行流程
### 1. 判断是否适合交给 Codex
适合：规则明确、写入边界清晰、产物可以文件化的任务。
不适合：目标模糊、写入范围不明、高风险且未拆分的大改动。

### 2. 创建任务卡
建议使用：
```bash
python E:\Obsidian\scripts\ai_bridge.py create-task --owner codex --title "<title>"
```

然后补全 frontmatter，并写清楚：
- `inputs`
- `allowed_write_paths`
- `expected_output`
- `rollback`

### 3. dry-run 校验
```bash
python E:\Obsidian\scripts\bridge_runner.py --task "E:\Obsidian\.ai-bridge\tasks\TASK-NNN-xxx.md" --dry-run
```

### 4. 正式执行
```bash
python E:\Obsidian\scripts\bridge_runner.py --task "E:\Obsidian\.ai-bridge\tasks\TASK-NNN-xxx.md"
```

Runner 内部调用：
```text
codex.cmd exec --skip-git-repo-check -s danger-full-access -
```

### 5. 验证正式产物
执行完成后，优先检查：
- 任务卡状态是否更新
- 结果卡是否存在且可按 UTF-8 读取
- 正式文件是否写在 `allowed_write_paths` 内
- 事件流是否记录了 `formal.output.validated`

### 6. 查看调试信息
可以查看：
- `G:\CodexTemp\TASK-NNN-<timestamp>.log`
- `E:\Obsidian\.ai-bridge\events\TASK-NNN-<timestamp>.jsonl`

但这些内容仅用于定位问题，不是正式文档来源。

## 事件说明
- `runner.received`：收到任务
- `task.snapshot`：任务卡快照
- `task.status`：任务状态更新
- `codex.started`：Codex 开始执行
- `codex.debug.stdout`：标准输出调试行
- `codex.debug.stderr`：标准错误调试行
- `codex.completed`：Codex 退出
- `formal.output.validated`：正式 UTF-8 产物校验通过
- `runner.completed` / `runner.failed` / `runner.error`：最终结果

## 失败处理
1. 先看结果卡状态。
2. 再看事件流定位失败阶段。
3. 最后看调试日志辅助定位。
4. 修复任务卡或代码后，再把任务状态改回 `pending` 重跑。

```bash
python E:\Obsidian\scripts\ai_bridge.py set-task-status --task-id TASK-NNN --status pending
python E:\Obsidian\scripts\bridge_runner.py --task "<path>"
```

---

## 已知问题与标准处置

### KI-1：Runner 报 "Task status is not done after Codex exit"（exit code 1）

**原因**：Codex 无法写入任务卡（任务卡路径不在 `allowed_write_paths` 内），导致 runner 认为任务未完成。

**判断产物是否实际已生成**：检查 `expected_output` 中的文件是否存在。

**修复流程**（产物已生成时）：

```bash
# Step 1：用 ai_bridge.py 设置状态（不依赖 Edit 工具，避免缓存冲突）
python "E:\Obsidian\scripts\ai_bridge.py" set-task-status --task-id TASK-NNN --status done

# Step 2：注入 JSONL 事件
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
JSONL="E:/Obsidian/.ai-bridge/events/TASK-NNN-<timestamp>.jsonl"
echo "{\"ts\":\"$NOW\",\"type\":\"task.status\",\"task_id\":\"TASK-NNN\",\"status\":\"done\"}" >> "$JSONL"
echo "{\"ts\":\"$NOW\",\"type\":\"runner.completed\",\"task_id\":\"TASK-NNN\",\"message\":\"Manually marked done: products verified\"}" >> "$JSONL"

# Step 3：刷新 dashboard
python "E:\Obsidian\scripts\bridge_event_snapshot.py"
```

> **注意**：永远不要用 Edit 工具修改任务卡状态。runner 会在执行期间修改任务卡，导致 Edit 的读缓存失效并报 "File has been modified since read" 错误。始终用 `ai_bridge.py set-task-status` 或 Bash 直接写。

---

### KI-2：Bash 中运行 Python 脚本用 `python`，不用 `python3`

**原因**：此 Windows 环境（D:\Python\Python312）只有 `python.exe`，没有 `python3`。调用 `python3` 返回 exit code 49（文件未找到）。

**规则**：所有 Bash 命令中一律使用 `python`，验证脚本同理。

---

### KI-3：结果卡为空模板

**原因**：Codex 有时不填充结果卡（优先完成主产物）。

**处置**：直接用 grep/python 验证主产物是否满足 Acceptance 条件；若满足，手动写入结果卡摘要，不影响主流程。

## 任务卡最小要求
```yaml
id: TASK-NNN
owner: codex
status: pending
created: YYYY-MM-DD
deadline: ~
scope: <精确范围>
inputs: [<读取路径>]
allowed_write_paths: [<严格写入路径>]
expected_output: <具体产物>
rollback: <失败回退方案>
notes: <额外约束>
```

## 结果卡最小要求
```yaml
task_id: TASK-NNN
status: done | partial | failed
files_created: [...]
files_modified: [...]
summary: <执行摘要>
risks: <风险说明>
next_step: <下一步建议>
```
