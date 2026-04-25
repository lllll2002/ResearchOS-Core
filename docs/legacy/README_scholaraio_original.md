# ScholarAIO

**Scholar All-In-One** — the research terminal. 科研终端。

> [中文版](#中文) ｜ [English](#english)

---

<a id="english"></a>

Imagine doing all your research — literature search, reading, discussion, analysis, writing — in one terminal, in natural language. No context-switching between apps, no manual bookkeeping. Just tell the AI what you need. (Wet-lab experiments not included.)

ScholarAIO makes this real. It pairs Claude Code with a research-grade infrastructure: high-quality PDF parsing (MinerU), hybrid search, topic modeling, citation graphs, and robust metadata pipelines. You talk; it reads, retrieves, discovers connections, drafts your literature review, generates analysis code, and exports your bibliography. One terminal, start to finish.

### Features

| | |
|---|---|
| **Deep PDF Parsing** | MinerU → structured Markdown with figures, tables, and equations preserved |
| **Hybrid Search** | FTS5 keyword + Qwen3 semantic + FAISS → RRF fusion ranking |
| **Topic Discovery** | BERTopic clustering + 6 interactive HTML visualizations |
| **Journal Exploration** | Fetch entire journals via OpenAlex → embed → cluster → semantic search |
| **Citation Graph** | References, citing papers, shared references across your library |
| **Layered Reading** | L1 metadata → L2 abstract → L3 conclusion → L4 full text — read at the depth you need |
| **Multi-Source Import** | Endnote XML/RIS, Zotero (Web API + local SQLite), PDF, Markdown |
| **Workspaces** | Organize papers into projects with scoped search and BibTeX export |
| **Academic Writing** | Literature review, paper drafting, citation verification, rebuttal, research gap analysis |
| **MCP Server** | 36 tools for Claude Desktop, Cursor, and any MCP client |

### Quick Start

```bash
git clone https://github.com/ZimoLiao/scholaraio.git && cd scholaraio
pip install -e ".[full]"    # or `pip install -e .` for minimal
```

Then launch Claude Code in the project directory and say "help me set up" — it handles the rest.

Or configure manually:

```bash
claude                              # Claude Code (recommended)
scholaraio-mcp                      # MCP server
scholaraio search "drag reduction"  # CLI
```

### Configuration

Main config: `config.yaml` (tracked). Secrets: `config.local.yaml` (gitignored). Quick setup: `cp config.local.example.yaml config.local.yaml` and fill in your keys.

| Key | What it does | How to get it |
|-----|-------------|---------------|
| `DEEPSEEK_API_KEY` | LLM backend — metadata extraction, content enrichment, scholarly discussion | [DeepSeek](https://platform.deepseek.com/) (default) or any OpenAI-compatible API |
| `MINERU_API_KEY` | PDF → high-quality structured Markdown | Free tier at [mineru.net](https://mineru.net/apiManage/token). Or [self-host MinerU](https://github.com/opendatalab/MinerU) |

> Both optional. Without LLM key: regex-only extraction. Without MinerU key: place `.md` files in `data/inbox/` directly.

Embedding model (Qwen3-Embedding-0.6B, ~1.2GB) auto-downloads on first use. Default source: ModelScope. Set `embed.source: huggingface` for international users.

Full config reference: [`config.yaml`](config.yaml)

### License

[MIT](LICENSE) © 2026 Zi-Mo Liao

---

<a id="中文"></a>

想象一下：文献检索、阅读、讨论、分析、写作——全部在一个终端里，用自然语言完成。不用在多个软件之间切换，不用手动整理。你只需要说出你要什么。（做实验的除外。）

ScholarAIO 让这件事成为现实。它将 Claude Code 与一套科研级基础设施结合：高质量 PDF 解析（MinerU）、融合检索、主题建模、引用图谱、鲁棒的元数据流水线。你说话，它读论文、检索文献、发现关联、起草综述、生成分析代码、导出参考文献。一个终端，从头到尾。

### 核心功能

| | |
|---|---|
| **深度 PDF 解析** | MinerU → 结构化 Markdown，图表、公式完整保留 |
| **融合检索** | FTS5 关键词 + Qwen3 语义向量 + FAISS → RRF 排序融合 |
| **主题发现** | BERTopic 自动聚类 + 6 种交互式 HTML 可视化 |
| **期刊探索** | OpenAlex 拉取期刊全量论文 → 向量化 → 聚类 → 语义搜索 |
| **引用图谱** | 参考文献 / 被引论文 / 共同引用，全库或工作区范围查询 |
| **分层阅读** | L1 元数据 → L2 摘要 → L3 结论 → L4 全文——按需加载，不浪费上下文 |
| **多源导入** | Endnote XML/RIS、Zotero（Web API + 本地 SQLite）、PDF、Markdown |
| **工作区** | 论文子集管理，支持范围内检索和 BibTeX 导出 |
| **学术写作** | 文献综述、论文起草、引用验证、审稿回复、研究空白分析 |
| **MCP 服务器** | 31 个工具，Claude Desktop / Cursor 等 MCP 客户端均可调用 |

### 快速开始

```bash
git clone https://github.com/ZimoLiao/scholaraio.git && cd scholaraio
pip install -e ".[full]"    # 或 `pip install -e .` 最小安装
```

然后在项目目录启动 Claude Code，说"帮我配置好这个项目"——剩下的它会搞定。

也可以手动使用：

```bash
claude                              # Claude Code（推荐）
scholaraio-mcp                      # MCP 服务器
scholaraio search "drag reduction"  # 命令行
```

### 配置

主配置：`config.yaml`（进 git）。敏感信息：`config.local.yaml`（不进 git）。快速配置：`cp config.local.example.yaml config.local.yaml` 然后填入密钥。

| Key | 用途 | 获取方式 |
|-----|------|---------|
| `DEEPSEEK_API_KEY` | LLM 后端——元数据提取、内容富化、学术讨论 | [DeepSeek](https://platform.deepseek.com/)（默认）或任意 OpenAI 兼容 API |
| `MINERU_API_KEY` | PDF → 高质量结构化 Markdown | [mineru.net](https://mineru.net/apiManage/token) 免费申请，也可[本地部署 MinerU](https://github.com/opendatalab/MinerU) |

> 均为可选。没有 LLM key：降级为纯正则提取。没有 MinerU key：直接将 `.md` 放入 `data/inbox/`。

嵌入模型（Qwen3-Embedding-0.6B，约 1.2GB）首次使用时自动下载。默认从 ModelScope 下载（国内无需代理），海外用户设置 `embed.source: huggingface`。

完整配置参考：[`config.yaml`](config.yaml)

### 许可证

[MIT](LICENSE) © 2026 Zi-Mo Liao
