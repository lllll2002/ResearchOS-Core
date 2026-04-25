---
name: lit-show
description: 查看 ScholarAIO 文献库中某篇论文的内容。支持 L1（元数据）、L2（摘要）、L3（结论）、L4（全文）四个层次。当用户说"看这篇论文"、"读一下"、"这篇的摘要/结论/全文"、"给我看 XX 的内容"时触发。
allowed-tools: Bash
---

# 查看论文内容

ScholarAIO 工具目录：`E:/scholaraio/scholaraio-main/scholaraio-main`

## 层次说明

| 层 | 内容 | 命令 |
|----|------|------|
| L1 | 元数据（title/authors/year/journal/doi） | `--layer 1` |
| L2 | 摘要 abstract | `--layer 2` |
| L3 | 结论 conclusion（需先 enrich-l3） | `--layer 3` |
| L4 | 完整 Markdown 全文 | `--layer 4` |

## 执行逻辑

1. 解析用户想看的论文（paper-id = `data/papers/` 下的目录名，格式如 `Author-Year-ShortTitle`）

2. 如果用户不知道 paper-id，先用 `lit-search` 帮用户找到目标论文

3. 判断层次：
   - 未指定 → 显示 L1+L2（元数据+摘要）
   - "摘要" → L2
   - "结论" → L3
   - "全文"/"完整内容" → L4（内容过长时先问用户是否确认）

4. 执行命令：

```bash
cd "E:/scholaraio/scholaraio-main/scholaraio-main" && scholaraio show "<paper-id>" --layer <N>
```

5. 针对相分离研究语境，对内容做简短解读：
   - L2/L3：指出与 Aim 1/Aim 4 的关联
   - L4：提示关键图表、公式所在章节，可进一步读取图片

6. 如需读取论文图表：
```bash
# 图片在 data/papers/<paper-id>/images/ 下
ls "E:/scholaraio/scholaraio-main/scholaraio-main/data/papers/<paper-id>/images/"
```

## 示例

用户说："看一下 Posey-2024-JACS 这篇的摘要"
→ `show "Posey-2024-JACS" --layer 2`

用户说："给我看这篇论文的结论"
→ `show "<当前上下文中的 paper-id>" --layer 3`

用户说："读一下 Taylor 模型那篇的全文"
→ 先搜索 `usearch "Taylor model droplet deformation"` 找到 paper-id，再 `show "<id>" --layer 4`
