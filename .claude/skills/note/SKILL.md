---
name: note
description: 为论文写入深读笔记，或调取已有笔记。笔记保存在论文目录的 notes.md 中，每次 show 时自动附带显示。
triggers:
  - "深读"
  - "写笔记"
  - "记录分析"
  - "加深印象"
  - "保存分析"
  - "保存笔记"
  - "查看笔记"
---

# 深读笔记

将对一篇论文的深度分析永久保存在该论文目录下的 `notes.md` 中。
每次通过 `scholaraio show` 查看该论文时，笔记会自动附带显示。

## 笔记文件位置

```
data/papers/<Author-Year-Title>/notes.md
```

## 笔记语言规范

**Primary language: English. Use the paper's original words and sentences — quote directly, distill key claims.**
Chinese annotations are secondary: wrap in `*（...）*` italic parentheses. They are visible to the user but I do not need to "read" them for comprehension — treat them as comments.

Template pattern:

```markdown
> "Original sentence or key phrase from the paper."  ← direct quote, bold key terms

*（中文注释：这句话的含义、背景或批判性判断）*
```

Rules:
- Every major claim → backed by a direct quote from the paper
- Numbers, method names, system names → use the paper's exact terminology
- Do NOT paraphrase into generic language if the original phrasing is precise
- Chinese annotations: add context, critique, or cross-paper connections the user may want to see at a glance
- At the end of every note, append a **"中文全文翻译"** section: a complete Chinese translation of all English content above. This section is for the user to read — I do not need to process it.

## 向用户解读论文时的引文规范

**当向用户口头解读（而非写入 notes.md）时，同样必须遵守：**

每个重要观点，附上论文原文引用：

```
**[观点描述]**

> "原文句子或段落（英文原句）"
```

规则：
- 解释每个核心论断时，紧跟论文原句（blockquote 格式）
- 若涉及数据/结论/方法，必须引用原文，不得只靠意译
- 引文后可用中文补充背景或批判性评论
- 原文较长时可截取关键句，用 `...` 省略中间部分

---

## 执行逻辑

### 写入笔记

1. 确认目标论文（通过搜索或直接指定目录名）
2. 用 Read 工具读取论文内容（L2 摘要或 L4 全文），进行深度分析
3. 将分析结果整理为结构化 Markdown 笔记，包含以下部分（按需选择）：

```markdown
# Deep Reading Notes · <Author Year> · <Title>

**Date**: <YYYY-MM-DD> | **Journal**: <...> | **DOI**: <...>

---

## Core Contribution / Definition

> "Direct quote defining the paper's central claim or concept."

*（中文注释）*

## Key Evidence / Results

> "Specific result sentence with numbers." (cited paper if referenced)

*（注释：实验条件、局限性）*

## Method / Architecture

> "Original description of the method."

*（注释：工程细节或关键参数）*

## Critical Assessment

**What holds up:** ...
**What needs scrutiny:** ...

> "Quote of a claim that needs scrutiny."

*（注释：为什么存疑）*

## Open Questions

- [ ] ...

## Links to Library

| Paper | Relation |
|-------|----------|
| Author Year (Title) | ... |

---

## 中文全文翻译

*以下为上述英文内容的中文翻译，供参考阅读，无需被 AI 处理。*

### 核心贡献 / 定义

> "（对应英文引用的中文翻译）"

### 关键证据 / 结果

> "..."

### 方法 / 架构

> "..."

### 批判性评估

**站得住脚的：** ...
**需要审视的：** ...

### 待追踪问题

- [ ] ...

### 与本库论文的关联

| 论文 | 关系 |
|------|------|
| 作者 年份（标题） | ... |
```

4. 用 Write 工具直接写入（新建）或 Edit 工具追加（已有笔记）到 `notes.md`

### 查看笔记

```bash
scholaraio note <paper-id>
```

或直接读取文件：

```bash
# 用 Read 工具读取
data/papers/<Author-Year-Title>/notes.md
```

### 笔记在 show 时自动显示

```bash
scholaraio show <paper-id> --layer 2
# → 输出摘要后，若存在 notes.md，自动附加"--- 深读笔记 ---"段落
```

## 写入方式

直接用工具写文件，**不需要通过 CLI `--file` 参数**：

```python
# 新建笔记
Write("data/papers/<dir>/notes.md", content)

# 追加笔记（已有 notes.md）
Edit("data/papers/<dir>/notes.md", append at end)
```

## 示例

用户说："帮我深度分析这篇论文并保存分析结果"
→ 读取论文 L4 全文 → 分析 → Write notes.md

用户说："把刚才的分析保存到这篇论文里"
→ 将对话中已有的分析整理 → Write/Edit notes.md

用户说："查看这篇论文的笔记"
→ Read data/papers/<dir>/notes.md
→ 或 scholaraio note <paper-id>
