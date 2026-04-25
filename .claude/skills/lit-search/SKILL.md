---
name: lit-search
description: 在 ScholarAIO 本地文献库中检索论文。支持融合检索（关键词+语义）、语义检索、关键词检索、按作者搜索、按引用量排序。当用户说"搜文献"、"找论文"、"检索"、"查一下XX相关的"、"找某某的论文"、"引用最高的"时触发。
allowed-tools: Bash
---

# 文献检索

ScholarAIO 工具目录：`E:/scholaraio/scholaraio-main/scholaraio-main`
**所有命令必须在该目录下执行。**

## 执行逻辑

1. 解析用户意图，判断检索模式：
   - 默认：融合检索（`usearch`）——关键词+语义两路合并，最相关
   - 用户明确说"语义搜索"/"向量搜索"：`vsearch`
   - 用户明确说"关键词搜索"/"FTS"：`search`
   - 按作者（"找某某的论文"）：`search-author`
   - 按引用量（"引用最高"/"最经典"）：`top-cited`

2. 提取过滤参数：
   - `--top N`：返回数量（默认 10）
   - `--year YYYY` 或 `--year YYYY-YYYY`：年份范围
   - `--journal "名称"`：期刊过滤（模糊匹配）
   - `--type review`：文献类型过滤

3. 执行命令（必须 cd 到工具目录）：

```bash
# 融合检索（默认）
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio usearch "<query>" --top <N> [--year <Y>] [--journal <J>]

# 语义检索
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio vsearch "<query>" --top <N>

# 关键词检索
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio search "<query>" --top <N>

# 按作者
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio search-author "<author>" --top <N>

# 按引用量
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio top-cited --top <N> [--type review]
```

4. 呈现结果，标注命中来源：
   - `both`：关键词+语义都命中（最相关）
   - `fts`：仅关键词命中
   - `vec`：仅语义命中

5. 结合相分离研究背景，对结果做简短解读，指出哪些论文与当前研究最相关。

## 相分离研究关键词参考

phase separation, stress granules, liquid-liquid phase separation, LLPS, condensates, G3BP1, eIF2α, electric field, electrophoresis, droplet deformation, Taylor model, dielectrophoresis, biomolecular condensates

## 示例

用户说："搜一下应激颗粒和电场相关的文献"
→ `usearch "stress granules electric field" --top 10`

用户说："找 Posey 的论文"
→ `search-author "Posey" --top 10`

用户说："库里引用最高的综述有哪些"
→ `top-cited --top 10 --type review`

用户说："2022年以后的相分离文献"
→ `usearch "phase separation" --year 2022-`
