---
name: lit-topics
description: 用 BERTopic 分析文献库的主题分布，发现研究聚类和跨领域关联。当用户说"主题分布"、"聚类分析"、"库里都有哪些研究方向"、"帮我看看文献的主题"、"生成可视化"时触发。
allowed-tools: Bash
---

# 主题聚类分析

ScholarAIO 工具目录：`E:/scholaraio/scholaraio-main/scholaraio-main`

## 执行逻辑

1. 判断用户意图：
   - 查看概览（默认）→ `topics`
   - 构建/重建模型 → `topics --build` 或 `topics --rebuild`
   - 查看某主题详情 → `topics --topic <ID>`
   - 合并相似主题 → `topics --merge "1,6+3,5"` 或 `topics --reduce <N>`
   - 生成 HTML 可视化 → `topics --viz`

2. 执行命令：

```bash
# 查看主题概览
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio topics

# 构建主题模型（首次或重建）
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio topics --build

# 查看某主题下的论文
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio topics --topic <ID> --top 10

# 生成 6 张交互式 HTML 可视化图
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio topics --viz

# 算法合并到 N 个主题
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio topics --reduce <N>

# 手动合并（逗号=同组，+分隔不同组）
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio topics --merge "1,6,14+3,5"
```

3. **智能合并流程**（用户要求"合并相似主题"时）：
   a. 先运行 `topics` 获取概览
   b. 分析关键词，判断哪些主题属于同一研究方向（如 LLPS + condensates + phase separation 可归为一组）
   c. 生成合并方案，确认后执行 `--merge`

4. 结合相分离研究背景解读结果：
   - 标记与相分离、应激颗粒、电场生物物理相关的主题
   - 指出文献库中可能有用但未被关注的相邻研究方向

## 示例

用户说："看看库里的主题分布"
→ `scholaraio topics`

用户说："主题 3 里有哪些论文"
→ `scholaraio topics --topic 3 --top 20`

用户说："帮我把相似主题合并"
→ 先概览，分析，再 `--merge`

用户说："生成主题可视化图"
→ `scholaraio topics --viz`（HTML 文件保存在 `data/topics/`）
