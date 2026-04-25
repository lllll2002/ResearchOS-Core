---
name: lit-ws
description: 管理 ScholarAIO 工作区（论文子集）：创建、查看、搜索、导出特定研究主题的文献集合。当用户说"工作区"、"workspace"、"新建一个论文集"、"把这些论文加到项目里"时触发。
allowed-tools: Bash
---

# 工作区管理

ScholarAIO 工具目录：`E:/scholaraio/scholaraio-main/scholaraio-main`

工作区是文献库的论文子集，用于按研究项目或主题组织论文。支持范围内检索和 BibTeX 导出。

## 执行逻辑

1. 判断用户意图：

```bash
# 列出所有工作区
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio ws list

# 创建工作区
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio ws create <name>

# 查看工作区内容
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio ws show <name>

# 向工作区添加论文
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio ws add <name> "<paper-id>"

# 从工作区移除论文
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio ws remove <name> "<paper-id>"

# 在工作区内搜索
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio ws search <name> "<query>"

# 导出工作区 BibTeX
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio export bibtex --ws <name> -o "<output.bib>"

# 删除工作区
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio ws delete <name>
```

2. 为相分离研究推荐工作区结构：
   - `phase-sep-aim1`：Aim 1 核心论文（Posey 2024, Morotomi-Yano 2012, Hamada 2020）
   - `phase-sep-aim4`：Aim 4 电动力学论文（Taylor 模型、介电泳）
   - `stress-granules`：应激颗粒领域综合
   - `llps-methods`：LLPS 实验方法论文

## 示例

用户说："帮我建一个相分离 Aim1 的工作区"
→ `ws create phase-sep-aim1`，然后搜索并添加 Posey/Morotomi-Yano/Hamada 等

用户说："把这个工作区的参考文献导出"
→ `export bibtex --ws <name> -o "aim1-refs.bib"`
