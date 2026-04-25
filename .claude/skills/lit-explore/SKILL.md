---
name: lit-explore
description: 通过 OpenAlex 探索新文献，支持多维度过滤（期刊、关键词、作者、机构、年份、引用量），并自动向量化和聚类。当用户说"找新文献"、"探索期刊"、"OpenAlex 检索"、"发现相关研究"时触发。
allowed-tools: Bash
---

# 文献探索（OpenAlex）

ScholarAIO 工具目录：`E:/scholaraio/scholaraio-main/scholaraio-main`

探索不在本地库中的新文献。结果保存在独立的 `data/explore/` 数据集，不污染主库。

## 执行逻辑

1. 与用户确认探索目标：
   - 主题关键词（必须）
   - 可选过滤：期刊、作者、机构、年份范围、最低引用量、文献类型

2. 执行探索命令：

```bash
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio explore
```

`explore` 命令交互式引导用户配置过滤条件（9 维过滤）。

3. 探索完成后，可对 explore 数据集进行：
   - 向量化：`scholaraio embed --dataset explore`
   - 主题建模：`scholaraio topics --dataset explore`
   - 搜索：`scholaraio usearch "<query>" --dataset explore`

4. 找到有价值的论文后，引导用户入库：
```bash
# 将 explore 结果中的特定论文移入主库
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio pipeline
```

5. 结合相分离研究背景推荐探索策略：
   - 推荐期刊：Nature Cell Biology, eLife, PNAS, Biophysical Journal, PRL, Soft Matter
   - 关键词：phase separation, LLPS, condensates, stress granules, electric field, dielectrophoresis, Taylor deformation
   - 关注作者：Hyman AA, Brangwynne CP, Bhatt DL（电场+细胞）

## 示例

用户说："帮我找一些关于电场驱动相变的新文献"
→ `scholaraio explore`（交互式配置：keywords="electric field phase separation", year=2020-）

用户说："探索一下 eLife 上的应激颗粒研究"
→ 引导配置：journal="eLife", keywords="stress granules"
