---
name: obsidian-save
description: 将当前对话的输出/讨论内容保存到 Obsidian vault（E:\Obsidian\Scholaraio\outputs\）中，按日期文件夹和主题命名。
triggers:
  - "保存到obsidian"
  - "保存到ob"
  - "保存在obsidian"
  - "保存在ob"
  - "存到obsidian"
  - "存到ob"
  - "存在obsidian"
  - "存在ob"
---

# 保存到 Obsidian

将当前对话中的输出、分析、讨论内容保存到 Obsidian vault。

## 保存路径规则

```
E:\Obsidian\Scholaraio\outputs\<YYYY-MM-DD>\<主题名>.md
```

- 日期：使用今天的日期（YYYY-MM-DD 格式）
- 主题名：根据对话内容自动提炼，或使用用户指定的名称
- 若当天日期文件夹不存在，先创建

## 执行逻辑

1. **确认日期文件夹**：检查 `E:\Obsidian\Scholaraio\outputs\<今日日期>\` 是否存在，不存在则用 Bash 创建
2. **确定主题名**：
   - 用户指定了名字 → 直接使用
   - 用户未指定 → 根据对话内容自动提炼 2-6 个字的中文主题名
3. **整理内容**：将本次对话中的核心输出整理为结构化 Markdown，加上 frontmatter
4. **写入文件**：用 Write 工具写入目标路径

## 文件格式

```markdown
---
date: <YYYY-MM-DD>
tags: [scholaraio, <相关标签>]
---

# <主题名>

> 对话时间：<YYYY-MM-DD>

## 内容

<整理后的对话输出内容>
```

## 注意事项

- 只保存**有价值的输出内容**（分析、搜索结果、文献综述、讨论结论等），不保存闲聊
- 若同一天同一主题已有文件，询问用户是覆盖还是追加
- 保存完成后，告知用户完整文件路径

## 示例

用户说："保存到ob"
→ 提炼主题 → 检查/创建日期文件夹 → 整理内容 → Write 写入文件 → 报告路径

用户说："把刚才的分析保存在ob中，主题叫DNA计算综述"
→ 主题名 = "DNA计算综述" → 写入 `outputs\2026-03-22\DNA计算综述.md`
