---
name: lit-ingest
description: 将新 PDF 论文导入 ScholarAIO 文献库（解析、元数据提取、索引、向量化）。当用户说"导入论文"、"入库"、"添加这篇PDF"、"把这篇论文加进去"时触发。
allowed-tools: Bash
---

# 论文入库

ScholarAIO 工具目录：`E:/scholaraio/scholaraio-main/scholaraio-main`

## 执行逻辑

### 方式 A：通过 inbox 自动入库（推荐）

1. 将 PDF 复制到 inbox 目录：
```bash
cp "<source-pdf>" "E:/scholaraio/scholaraio-main/scholaraio-main/data/inbox/"
```

2. 运行入库流水线：
```bash
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio pipeline
```

流水线自动完成：PDF 解析（MinerU）→ 元数据提取 → API 补全（Crossref/S2/OpenAlex）→ DOI 去重 → 建目录 → FTS5 索引更新

### 方式 B：从 Endnote/Zotero 批量导入

```bash
# Endnote XML 导入
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio import-endnote "<path/to/export.xml>"

# Zotero 导入（Web API）
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio import-zotero --api-key <key>
```

### 入库后更新索引

```bash
# 更新 FTS5 索引
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio index

# 更新语义向量（供 vsearch/usearch 使用）
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio embed
```

### 数据质量检查

```bash
# 审计元数据质量
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio audit

# 修复问题
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio repair

# 补全缺失摘要
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio backfill-abstract
```

## 示例

用户说："把桌面上的 Taylor1966.pdf 加进文献库"
→ `cp "<path-to>/Taylor1966.pdf" "data/inbox/"` 然后 `pipeline`

用户说："inbox 里有几篇 PDF 了，帮我入库"
→ 直接 `pipeline`
