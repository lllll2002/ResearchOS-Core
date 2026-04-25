# ScholarAIO — 完整参考文档

> 本文件从 CLAUDE.md 外置，仅在需要时按需读取。日常操作不必加载。

---

## 架构

```
PDF → mineru.py → .md     （或直接放 .md 跳过 MinerU）
                   ↓
             extractor.py (Stage 1: 从 md 头部提取字段，支持 regex/auto/robust/llm)
             metadata/    (Stage 2: API 查询补全，输出 .json，重命名文件)
                   ↓
             pipeline.py  (DOI 去重检查)
               ├─ 有 DOI → data/papers/<Author-Year-Title>/meta.json + paper.md
               └─ 无 DOI → data/pending/（待人工确认）
                   ↓
             index.py → data/index.db (SQLite FTS5)
             vectors.py → data/index.db (paper_vectors 表)
             topics.py → data/topic_model/ (BERTopic, 复用 paper_vectors)
                   ↓
             cli.py → .claude/skills/ → Claude Code

explore.py — 期刊全量探索（独立数据流，与主库隔离）
workspace.py — 工作区论文子集管理（薄层，复用现有搜索/导出）
```

## 分层加载设计（L1-L4）

| 层 | 内容 | 来源 |
|----|------|------|
| L1 | title, authors, year, journal, doi, volume, issue, pages, publisher, issn | JSON 文件 |
| L2 | abstract | JSON 字段 |
| L3 | 结论段 | JSON 字段（需先运行 enrich-l3 提取） |
| L4 | 全文 markdown | 直接读 .md |

## data/ 目录结构

```
data/papers/<Author-Year-Title>/
    ├── meta.json    # L1+L2+L3 元数据（含 "id": "<uuid>"）
    ├── paper.md     # L4 来源（MinerU 输出）
    ├── images/      # MinerU 提取的图片
    └── layout.json  # MinerU 版面分析（可选）

data/inbox/          # 待入库 PDF
data/inbox-thesis/   # 学位论文 PDF（跳过 DOI 去重）
data/pending/        # 无 DOI 论文待确认

data/explore/<name>/ # OpenAlex 期刊探索（隔离数据流）
    ├── papers.jsonl, explore.db, faiss.index
    └── topic_model/ + viz/
```

- UUID 作为内部唯一标识，永不改变
- `papers_registry` 表提供 UUID ↔ DOI ↔ dir_name 双向查找
- thesis 自动入库（来自 thesis inbox 或 LLM 判定），不经过 pending

## 配置

主配置：`config.yaml`（进 git）| 敏感信息：`config.local.yaml`（不进 git）

LLM API key 查找顺序：config.local.yaml → SCHOLARAIO_LLM_API_KEY → DEEPSEEK_API_KEY → OPENAI_API_KEY

默认 LLM：DeepSeek (deepseek-chat)，OpenAI 兼容协议。
Extractor 默认：`robust`（regex + LLM 双跑）。

## 代码风格

- Docstrings：库模块 Google-style；CLI handler 不加
- 用户界面文本：中文
- 代码注释：英文，仅在逻辑不自明时

## Skills 列表（22 个）

知识库管理：search, show, enrich, ingest, topics, explore, graph, citations, index, workspace, export, import, rename, audit

学术写作：literature-review, paper-writing, citation-check, writing-polish, review-response, research-gap

系统运维：setup, metrics

新增 skill 流程：工具型先实现 Python → CLI → 测试 → SKILL.md；编排型直接写 SKILL.md。

## 新用户引导

1. `scholaraio setup check`（诊断）
2. `pip install -e .`（安装）
3. `scholaraio setup`（交互式配置）
4. 嵌入模型首次使用自动下载

## 多 Agent 兼容

| Agent | 指令文件 | Skills |
|-------|---------|--------|
| Claude Code | `CLAUDE.md` | `.claude/skills/` |
| Codex | `AGENTS.md` | `.agents/skills/` → `.claude/skills/` |
| Cursor/Windsurf/Cline | wrapper files | — |

Skills 采用 AgentSkills.io 开放标准。
