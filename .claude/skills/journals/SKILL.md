---
name: journals
description: Query journal metrics — CAS partition (Q1-Q4), Top journal flag, and Open Access flag for papers in the knowledge base. Data sourced from 2025 CAS Journal Partition Table.
triggers:
  - "期刊分区"
  - "影响因子"
  - "中科院分区"
  - "几区"
  - "top期刊"
  - "journal partition"
  - "CAS quartile"
  - "which journal"
  - "journal ranking"
---

# 期刊分区查询

查询论文库中期刊的中科院分区信息（来源：2025年中科院期刊分区表）。

## 数据来源

`reviewer-memory/journals.json` — 从 2025 中科院期刊分区表 Excel 中提取，覆盖论文库中已知的期刊。

字段说明：
- `partition`：分区（1=Q1, 2=Q2, 3=Q3, 4=Q4）
- `is_top`：是否为 Top 期刊
- `is_oa`：是否为开放获取期刊

## 执行逻辑

1. 读取 `reviewer-memory/journals.json`
2. 根据用户问题，查询指定期刊或汇总展示
3. 如需结合论文库（如"我库里Q1的论文有哪些"），读取 `data/papers/*/meta.json` 匹配

## 示例查询

**"这篇论文在几区？"**
→ 读取该论文 meta.json 获取 journal，查询 journals.json

**"我库里所有Q1论文"**
→ 遍历 meta.json，与 journals.json 对比，列出 partition==1 的论文

**"Top期刊有哪些？"**
→ 过滤 journals.json 中 is_top==true 的期刊

**"Nature在几区？"**
→ 在 journals.json 中查找 "Nature"

## 覆盖范围说明

- 会议论文、预印本（arXiv、bioRxiv）无 CAS 分区
- 部分新期刊（如 Nature Reviews Bioengineering、Antikythera）尚未收录于 2025 CAS 表
- 未匹配期刊不代表质量低，可能是新期刊或特殊出版物
