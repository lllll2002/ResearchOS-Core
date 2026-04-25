---
name: enrich
description: Enrich paper metadata using LLM extraction. Extract table of contents (TOC), conclusions (L3), backfill abstracts, or refetch citation counts from APIs. Use when the user wants to extract conclusions, build TOC, update citation data, or backfill missing abstracts.
---

# 富化论文内容

通过 LLM 提取论文的目录结构（TOC）或结论段（L3），丰富论文元数据。

## 执行逻辑

1. 解析用户意图：
   - **提取目录**：使用 `enrich-toc`
   - **提取结论**：使用 `enrich-l3`
   - **补全摘要**：使用 `backfill-abstract`（从 .md 提取 + LLM 校验）
   - **补查引用量**：使用 `refetch`（重新查询 API 补全 citation_count 等字段）

2. 确定处理范围：
   - 指定论文 ID → 处理单篇
   - 用户说"全部" → 使用 `--all`
   - 可选 `--force` 覆盖已有结果

3. 执行命令：

**提取目录：**
```bash
scholaraio enrich-toc [<paper-id> | --all] [--force]
```

**提取结论：**
```bash
scholaraio enrich-l3 [<paper-id> | --all] [--force]
```

**补全摘要：**
```bash
scholaraio backfill-abstract [--dry-run]
```

**补查引用量：**
```bash
scholaraio refetch [<paper-id> | --all] [--force]
```

4. 展示处理结果。

## 示例

用户说："帮我提取所有论文的结论"
→ 执行 `enrich-l3 --all`

用户说："重新提取 Smith-2023-Survey 的目录"
→ 执行 `enrich-toc "Smith-2023-Survey" --force`

用户说："补全摘要"
→ 执行 `backfill-abstract`，然后提示 `embed --rebuild`

用户说："补查引用量"
→ 执行 `refetch --all`，然后 `index --rebuild`
