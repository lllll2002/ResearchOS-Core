# ScholarAIO — Claude Code 项目指令

## 记忆系统

**唯一记忆位置**：`reviewer-memory/MEMORY.md`（本项目内）。禁止读写 `C:\Users\` 下的记忆路径。只在用户明确要求时更新记忆。

## 项目定位

围绕 Claude Code 构建的科研终端。`scholaraio` Python 包提供基础设施（PDF 解析、融合检索、主题建模、引用图谱、知识图谱），Claude Code 负责理解意图、调度工具、整合结果、参与学术讨论。

**学术态度**：论文结论是作者的宣称，不是真理。以成熟学者姿态对待文献——不迷信权威、交叉验证、辩证讨论、区分事实与观点。

## 模块概览

| 模块 | 功能 |
|------|------|
| `ingest/` | PDF → MinerU Markdown → 元数据提取 → API 补全 → 入库流水线 |
| `index.py` | FTS5 全文检索 + papers_registry + citations 引用图谱 |
| `vectors.py` | Qwen3 语义向量 + FAISS + 结构化分块（sub-section + 滑动窗口） |
| `nlquery.py` | Text-to-SQL 自然语言查询 + 意图路由（search/data/graph） |
| `kgraph.py` | 知识图谱：实体/关系抽取 + LLM 增强 + pyvis 可视化 |
| `topics.py` | BERTopic 主题建模 + 可视化 |
| `loader.py` | L1-L4 分层加载 + enrich_toc + enrich_l3 |
| `explore.py` | OpenAlex 期刊全量探索 |
| `workspace.py` | 工作区论文子集管理 |
| `audit.py` | 数据质量审计 + 修复 |
| `mcp_server.py` | MCP 服务端（36 tools） |

CLI：`scholaraio --help` | 关键命令：`ask`（智能路由）、`usearch`（融合检索）、`nlsearch`（NL→SQL）、`kg`（知识图谱）

## 关键约定

- 用户输出放 `workspace/` 目录，不放项目根或 `scholaraio/` 源码目录
- 不修改 `metadata/_extract.py` 正则逻辑，只通过 extractor 抽象层扩展
- `data/`、`workspace/` 不进 git
- Python 3.10+
- Docstrings：库模块 Google-style；CLI handler 不加；UI 文本中文；注释英文

## 完整参考

架构图、目录结构、配置详情、skill 列表、多 Agent 兼容表：见 `docs/REFERENCE.md`
