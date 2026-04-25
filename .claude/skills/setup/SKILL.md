---
name: setup
description: Initialize and diagnose the ScholarAIO environment. Run interactive setup wizard (bilingual EN/ZH) to install dependencies, create config files, and configure API keys. Run status check to see what's installed and what's missing. Use when the user wants to set up, install, configure, or troubleshoot ScholarAIO.
---

# Setup / 环境配置

当用户需要配置、安装、初始化 ScholarAIO 时，按以下流程操作：

## 1. 诊断当前状态

```bash
scholaraio setup check --lang zh
```

阅读输出，了解哪些组件已就绪、哪些缺失。

## 2. 根据缺失项引导用户

### 依赖缺失
- 告诉用户缺少哪些依赖，解释每组依赖的用途：
  - `embed`: 语义向量检索（Qwen3 嵌入模型）
  - `topics`: BERTopic 主题建模
  - `import`: Endnote / Zotero 导入
  - `full`: 全部功能
- 运行 `pip install -e ".[full]"` 或按需安装

### config.yaml 缺失
- 运行 `scholaraio setup` 交互式向导自动创建
- 或者直接帮用户创建（默认配置即可）

### API key 未配置
- **LLM key**（DeepSeek / OpenAI）：问用户是否有。没有也能用，但元数据提取降级为纯正则、enrich 不可用
- **MinerU key**：问用户是否需要处理 PDF。不需要则跳过（只入库 .md 文件）
- 将密钥写入 `config.local.yaml`（不进 git）

### 目录不存在
- 运行 `scholaraio setup check` 后如果目录缺失，运行任意 scholaraio 命令会自动创建（`ensure_dirs()`）

## 3. 验证

配置完成后再次运行 `scholaraio setup check` 确认所有项目 [OK]。

## 注意

- 用户也可以直接运行 `scholaraio setup` 进入交互式向导（bilingual EN/ZH）
- `config.local.yaml` 存放敏感信息（API key），不进 git
- 嵌入模型（~1.2GB）会在首次 embed/vsearch 时自动下载，setup 不触发下载
