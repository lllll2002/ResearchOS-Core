# Skill 任务卡专用模板

> 适用于：创建新 skill 或更新现有 skill
> 使用方式：复制此模板，填入具体内容，保存为 `TASK-NNN-create-<skill-name>-skill.md`

---

```markdown
---
id: TASK-NNN
owner: codex
status: pending
created: YYYY-MM-DD
deadline: ~
scope: E:\Obsidian\.claude\skills\<skill-name>
inputs:
  - E:\Obsidian\.ai-bridge\tasks\TASK_TEMPLATE.md
  - E:\Obsidian\.claude\skills\<参考 skill>\SKILL.md   # 风格参考
allowed_write_paths:
  - E:\Obsidian\.claude\skills\<skill-name>
  - E:\Obsidian\.ai-bridge\results
expected_output:
  - E:\Obsidian\.claude\skills\<skill-name>\SKILL.md（新建 or 更新）
  - （可选）E:\Obsidian\.claude\skills\<skill-name>\scripts\<script>.py
  - （可选）E:\Obsidian\.claude\skills\<skill-name>\references\<ref>.md
  - SKILL.md 通过 bash -n 或 py_compile 语法检查
  - 结果卡写入 E:\Obsidian\.ai-bridge\results\TASK-NNN-result.md
rollback: >
  新建：失败时删除 E:\Obsidian\.claude\skills\<skill-name>\ 整个目录。
  更新：失败时用 git checkout 或手动还原原始 SKILL.md 内容。
notes: >
  遵守 skill-creator 规范；frontmatter 必须包含 name/description/trigger_on；
  token 节省优先，不写多余注释；不得写入 allowed_write_paths 以外的路径。
---

## Task

在 `E:\Obsidian\.claude\skills\<skill-name>\` 下<新建/更新>一个名为 `<skill-name>` 的 Claude Code skill。

**skill 用途：** <一句话描述>

**触发条件：** <用户说什么时触发>

**核心行为：**
- <行为 1>
- <行为 2>
- <行为 3>

**（如有）scripts/ 需求：**
- `scripts/<script>.py`：<用途>

**（如有）references/ 需求：**
- `references/<ref>.md`：<用途>

**验证要求：**
- [ ] SKILL.md 包含正确 frontmatter（name, description, trigger_on）
- [ ] 核心行为步骤可执行
- [ ] bash -n 或 py_compile 语法检查通过（如有脚本）
- [ ] 不写入 allowed_write_paths 以外的路径

## Acceptance

- [ ] `E:\Obsidian\.claude\skills\<skill-name>\SKILL.md` 文件存在
- [ ] frontmatter 完整
- [ ] 结果卡存在于 `E:\Obsidian\.ai-bridge\results\TASK-NNN-result.md`

## Execution Notes

- 参考 `close-day/SKILL.md` 的文件结构风格
- 优先复用已有脚本（`E:\Obsidian\scripts\`）
- 如果需要 Bash，注意 Windows 环境下路径用反斜杠
```

---

## 常用 allowed_write_paths 示例

**仅新建 skill，无额外脚本：**
```yaml
allowed_write_paths:
  - E:\Obsidian\.claude\skills\<skill-name>
  - E:\Obsidian\.ai-bridge\results
```

**新建 skill + 共享脚本：**
```yaml
allowed_write_paths:
  - E:\Obsidian\.claude\skills\<skill-name>
  - E:\Obsidian\scripts
  - E:\Obsidian\.ai-bridge\results
```

**只更新现有 SKILL.md：**
```yaml
allowed_write_paths:
  - E:\Obsidian\.claude\skills\<skill-name>\SKILL.md
  - E:\Obsidian\.ai-bridge\results
```

---

## rollback 模板

**新建 skill：**
```
本任务为新建。失败时删除 E:\Obsidian\.claude\skills\<skill-name>\ 整个目录，无其他副作用。
```

**更新现有 skill（有备份）：**
```
更新前已备份原始 SKILL.md 到 E:\Obsidian\.ai-bridge\backup\<skill-name>-SKILL-backup.md。
失败时从备份恢复。
```

**只读审计：**
```
本任务只读，无需回滚。
```
