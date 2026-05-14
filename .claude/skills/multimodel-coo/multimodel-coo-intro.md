# multimodel-coo · 使用介绍

> **一句话**：把复杂任务按难度自动分配给最合适的模型，Claude 负责总控，你来拍板。

---

## 这个 skill 是干什么的

正常情况下，所有任务都由 Claude 直接处理。
当任务超出单次处理的合理范围时，`multimodel-coo` 把任务拆开，分配给专项模型执行：

| 模型 | 擅长什么 |
|------|---------|
| **Qwen3:8b**（本地） | 任务拆解、task card 草稿、模板生成 |
| **DeepSeek** | 复杂推理、失败模式分析、多方案权衡 |
| **Codex** | 代码执行、脚本、批处理、文件操作 |
| **GLM** | 风险审计、任务卡 review、实现检查 |
| **Claude / Opus** | 顶层控制、路由决策、最终整合 |

模型之间通过**阶段文件**传递上下文（不是实时对话），每个节点的输出写入文件，下一个节点读取继续。

---

## 如何触发

```
/multimodel-coo          # 无参数，Claude 自动分析并提案
/multimodel-coo -1       # 指定模式 -1
/multimodel-coo -2       # 指定模式 -2
/multimodel-coo -3       # 指定模式 -3
打开多模型               # 中文触发词
多模型处理这个           # 同上
use multi-model          # 英文触发词
```

或者在描述任务时包含这些信号词，skill 也会自动触发：
- "帮我批量修改所有文件"（→ 识别为执行+风险型）
- "分析一下这个假设的边界条件"（→ 识别为推理型）
- "需要跨模块重构"（→ 识别为架构型）

---

## 四条链路

### 链路 -1｜简单执行
```
Claude → Qwen → Codex（可选）→ Claude
```
适用：规则明确的批处理、模板生成、小代码任务、格式转换

### 链路 -2｜风险型执行
```
Claude → Qwen → GLM审核 → Codex → GLM审核 → Claude
```
适用：批量写入/覆盖文件、scope 较宽、操作不可逆的任务
GLM 在执行前审 task card，执行后审实现，两道门禁。

### 链路 -3｜推理密集
```
Claude → Qwen → Claude          （中等推理）
Claude → DeepSeek → Claude      （难推理）
```
适用：失败模式分析、假设验证、边界条件推导、多方案比较
不需要代码执行，结果写入 `20_reasoning.md`。

### 链路 -4｜复杂架构（谨慎使用）
```
Opus → DeepSeek → Codex → GLM → Opus
```
适用：跨模块重构、软件架构设计、长期研究规划（>2周跨度）
不会自动触发，Claude 会明确提示"建议升级到 -4"后由你决定。

---

## 完整交互流程

```
你：/multimodel-coo  +  任务描述
        ↓
Claude：运行 preflight（检查 Ollama / API key 是否可用）
        ↓
Claude：提案卡
  ┌─────────────────────────────────────────┐
  │ 📋 任务分析                              │
  │ 推荐链路：-2（原因：批量写入+无rollback） │
  │                                         │
  │ 📌 所有可用链路                          │
  │   -1  Claude→Qwen→Codex→Claude          │
  │   -2  Claude→Qwen→GLM→Codex→GLM→Claude  │
  │   -3  Claude→DeepSeek→Claude            │
  │   -4  Opus→DeepSeek→Codex→GLM→Opus      │
  │                                         │
  │ ⚙️ 环境状态                              │
  │   Qwen: ✅  DeepSeek: ✅  GLM: ✅        │
  │                                         │
  │ 请确认或切换链路 →                       │
  └─────────────────────────────────────────┘
        ↓
你：确认 / -1 / -3 / 手动
        ↓
Claude：实时执行，每个节点完成后汇报状态
  ▶ [Qwen] 正在拆解...
  ✅ [Qwen] 完成 → 10_plan.md
  ▶ [GLM] 审核任务卡...
  ✅ [GLM] 通过 → 40_review.md
  ▶ [Codex] 执行中...
  ✅ [Codex] 完成 → 30_implementation.md
        ↓
Claude：完成汇报 + 归档建议
```

---

## 阶段文件（每个节点的"交接文档"）

```
E:\Obsidian\01_Planning\workflows\current_task\
├── 00_request.md        ← 任务描述
├── 10_plan.md           ← Qwen 拆解计划
├── 20_reasoning.md      ← DeepSeek/Qwen 推理结果
├── 30_implementation.md ← Codex 执行产物
├── 40_review.md         ← GLM 审核结果
├── 50_summary.md        ← Claude 最终总结
└── task_board.md        ← 任务看板
```

任务完成后，用以下命令归档：
```bash
python "E:\Obsidian\scripts\archive_current_task.py"
```

---

## 什么时候不需要用这个 skill

- 任务简单，Claude 一次回复就能解决 → 直接问 Claude
- 只需要文献搜索 → 用 `lit-search`
- 只需要 Codex 执行一个明确任务 → 用 `codex-caller`
- 不确定要不要用 → 描述任务，Claude 会判断并建议

---

## 常见问题

**Q：如果 Qwen 本地服务没开怎么办？**
preflight 会检测到并在提案中注明，Claude 会提供跳过 Qwen 直接走 DeepSeek 的降级方案。

**Q：我可以中途改变链路吗？**
可以。任何一个节点完成后，你都可以说"接下来不用 GLM 了"或"换成 DeepSeek 继续"。

**Q：-4 什么时候真正需要？**
极少数情况：整个系统架构重设计、跨项目长期规划、需要 Opus 级别的最终 synthesis。
日常任务几乎不需要 -4。

---

*skill 路径：`E:\Obsidian\.claude\skills\multimodel-coo\`*
*最后更新：2026-04-03*
