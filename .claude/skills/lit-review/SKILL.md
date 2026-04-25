---
name: lit-review
description: 基于 ScholarAIO 文献库撰写结构化文献综述。当用户说"写综述"、"帮我写文献综述"、"整理一下相关文献"、"survey"、"Related Work"时触发。
allowed-tools: Bash, Read, Write, Edit
---

# 文献综述写作

ScholarAIO 工具目录：`E:/scholaraio/scholaraio-main/scholaraio-main`

## 执行流程

### 1. 确认写作需求

向用户确认：
- **综述主题**（如"电场调控相分离"、"LLPS 在应激响应中的作用"）
- **目标读者**：期刊 Related Work / 学位论文综述章节 / 独立 review
- **语言**：中文 / English / 双语
- **篇幅**：大致字数
- **工作区**（可选）：是否有预设的 `ws` 工作区

### 2. 摸底文献范围

```bash
# 融合检索确认覆盖范围
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio usearch "<主题>" --top 20

# 查看主题聚类（如已建模）
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio topics

# 如有工作区，查看成员
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio ws show <name>
```

逐篇扫描核心论文 L1+L2（元数据+摘要）：
```bash
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio show "<paper-id>" --layer 2
```

### 3. 构建综述骨架

根据文献内容，提出分组方案，形成章节大纲，向用户确认。

常用组织方式（相分离研究常见）：
- **机制导向**：LLPS 驱动力 → 调控因子 → 生物学功能
- **扰动手段**：化学干预 → 物理干预（温度/电场/光）→ 遗传干预
- **技术路线**：体外重构 → 细胞实验 → 计算模型

### 4. 深度阅读关键论文

```bash
# 读结论
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio show "<paper-id>" --layer 3

# 读全文（仅关键论文）
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio show "<paper-id>" --layer 4

# 共同引用分析（发现领域基础论文）
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio shared-refs "<id1>" "<id2>"
```

### 5. 撰写综述

**语言规则**：
- 双语需求：先写英文版 → 再译中文版
- 输出保存到 `03_Theoretical_Work/` 或用户指定目录

**写作原则**：
- 综合而非罗列：每段围绕一个论点组织多篇文献
- 批判性视角：指出方法局限、结论矛盾
- 引用格式：`(Author, Year)` 或 `Author (Year)`
- 每主要章节至少有 1 张概念图或汇总表格

每写完一节，暂停让用户确认再继续。

### 6. 导出 BibTeX

```bash
scholaraio export bibtex --all -o "references.bib"
```

## 学术态度

论文结论是作者的宣称，不是真理。综述应体现辩证思考。当多篇论文对同一问题有不同结论时，主动指出分歧并分析原因。
