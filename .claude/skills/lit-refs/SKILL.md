---
name: lit-refs
description: 分析论文引用关系：查看参考文献、被引论文、共同引用。当用户说"这篇引用了哪些"、"谁引用了这篇"、"参考文献"、"被引"、"共同引用"、"引用图谱"时触发。
allowed-tools: Bash
---

# 引用关系分析

ScholarAIO 工具目录：`E:/scholaraio/scholaraio-main/scholaraio-main`

## 执行逻辑

1. 判断用户意图：
   - "这篇的参考文献"/"引用了哪些" → `refs`
   - "谁引用了这篇"/"被哪些文章引用" → `citing`
   - "A 和 B 的共同引用"/"两篇的交叉" → `shared-refs`
   - 按引用量排序 → `top-cited`（见 lit-search）

2. 确认 paper-id（`data/papers/` 下的目录名），如不知道先用 `lit-search` 查找

3. 执行命令：

```bash
# 查看参考文献列表（该论文引用了哪些）
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio refs "<paper-id>"

# 查看被引论文（哪些论文引用了该篇）
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio citing "<paper-id>"

# 共同引用分析（A 和 B 都引用了哪些论文）
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio shared-refs "<paper-id-A>" "<paper-id-B>"

# 查看引用图（需先构建图）
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio graph "<paper-id>"
```

4. 解读引用关系的研究意义：
   - 共同引用的论文往往是领域基础性工作
   - 引用某篇关键论文的最新文章反映前沿进展
   - 可用于发现与相分离/电场研究相关的重要论文

## 示例

用户说："Posey 2024 那篇引用了哪些文献"
→ 先搜索确认 paper-id，再 `refs "<id>"`

用户说："谁引用了 Taylor 液滴形变那篇"
→ `citing "<taylor-paper-id>"`

用户说："Morotomi-Yano 2012 和 Hamada 2020 的共同引用是什么"
→ `shared-refs "<id1>" "<id2>"`（发现两篇论文共同的理论基础）
