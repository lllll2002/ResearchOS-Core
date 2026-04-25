---
name: explore
description: Explore journals by fetching all papers from OpenAlex, building local embeddings, running BERTopic clustering, and FAISS semantic search. Data is isolated in data/explore/<name>/. Use when the user wants to survey a journal, discover research trends in a specific publication, or do landscape analysis.
---

# 期刊探索

从 OpenAlex 拉取期刊全量论文，本地嵌入 + BERTopic 聚类，用于文献调研。数据与主库完全隔离。

## 执行逻辑

### 拉取期刊论文

```bash
scholaraio explore fetch --issn <ISSN> --name <名称> [--year-range <起-止>]
```

常用期刊 ISSN：
- JFM (Journal of Fluid Mechanics): 0022-1120
- PoF (Physics of Fluids): 1070-6631
- JCP (Journal of Computational Physics): 0021-9991
- IJMF (Int J Multiphase Flow): 0301-9322

### 生成嵌入

```bash
scholaraio explore embed --name <名称> [--rebuild]
```

### 主题聚类

```bash
scholaraio explore topics --name <名称> --build
scholaraio explore topics --name <名称> --rebuild --nr-topics <N>
scholaraio explore topics --name <名称>
scholaraio explore topics --name <名称> --topic <ID> [--top N]
```

### 语义搜索

```bash
scholaraio explore search --name <名称> "<查询词>" [--top N]
```

### 生成可视化

```bash
scholaraio explore viz --name <名称>
```

### 查看探索库信息

```bash
scholaraio explore info
scholaraio explore info --name <名称>
```

对于全新期刊，完整流程是：fetch → embed → topics --build → viz

## 示例

用户说："帮我拉取 JFM 的全部论文"
→ 执行 `explore fetch --issn 0022-1120 --name jfm`

用户说："在 JFM 里搜 drag reduction"
→ 执行 `explore search --name jfm "drag reduction"`

用户说："生成 JFM 的可视化"
→ 执行 `explore viz --name jfm`

用户说："我有哪些探索库"
→ 执行 `explore info`
