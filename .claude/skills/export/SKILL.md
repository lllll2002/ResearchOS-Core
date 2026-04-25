---
name: export
description: Export papers from the knowledge base to standard citation formats like BibTeX. Supports exporting all papers, specific papers, or filtered by year/journal. Use when the user needs BibTeX entries, reference files, or citation export.
---

# 导出论文

将本地论文库中的论文导出为标准引用格式（BibTeX）。

## 执行逻辑

**导出全部论文到屏幕：**
```bash
scholaraio export bibtex --all
```

**导出全部论文到文件：**
```bash
scholaraio export bibtex --all -o workspace/library.bib
```

**导出指定论文：**
```bash
scholaraio export bibtex "Smith-2023-Turbulence" "Doe-2024-DNS"
```

**按年份筛选导出：**
```bash
scholaraio export bibtex --all --year 2020-2024 -o workspace/recent.bib
```

**按期刊筛选导出：**
```bash
scholaraio export bibtex --all --journal "Fluid Mechanics" -o workspace/jfm.bib
```

## 示例

用户说："把我所有论文导出成 BibTeX"
→ 执行 `export bibtex --all`

用户说："导出 2020 年以后的论文到 bib 文件"
→ 执行 `export bibtex --all --year 2020- -o workspace/recent.bib`

用户说："把这篇 Smith-2023-Turbulence 的引用给我"
→ 执行 `export bibtex "Smith-2023-Turbulence"`

用户说："导出 DNS 相关的论文引用"
→ 先用 `usearch "DNS"` 搜索，从结果中提取目录名，再 `export bibtex <dir1> <dir2> ...`
