---
name: ppt
description: Generate a Gamma presentation (PPT) from research papers in the knowledge base or from user-provided content. Searches the library, builds structured slide content, calls the Gamma API, and returns the presentation URL. Use when the user wants to create slides, a presentation, or export a PPT from their research.
---

# PPT 生成（Gamma）

调用 Gamma API 根据文献库内容或用户指定主题生成演示文稿。

## 执行流程

### 1. 了解需求

向用户确认（未说明的才问）：
- **主题**：要做什么方向的 PPT？
- **内容来源**：从知识库搜索相关文献 / 用户直接提供内容 / 两者结合
- **幻灯片数量**：建议 8-15 张，可指定
- **语言**：中文（zh-CN）/ 英文（en-US）
- **导出格式**：只看在线版（gammaUrl）/ 同时下载 PPTX（加 `--export`）

### 2. 从知识库收集内容（如需）

```bash
# 语义检索相关论文
scholaraio search "<主题>" --mode semantic --top 10

# 查看摘要和结论
scholaraio show <dir_name> --level 2
scholaraio show <dir_name> --level 3

# 查看主题聚类
scholaraio topics

# 工作区内检索（如有）
scholaraio ws search <ws_name> "<主题>"
```

### 2b. 收集论文图片

对每篇相关论文，检查是否有可用图片：

```bash
# 查看论文的 images/ 目录
ls data/papers/<dir_name>/images/
```

对找到的图片：
1. 用 Read 工具读取图片，判断是否与当前幻灯片内容相关
2. 记录图片路径和来源论文（第一作者姓氏 + 年份），格式：`姓, 年份`
3. 在 inputText 对应幻灯片中注明图片插入位置（见下方格式）

**引用规则**：
- 使用了论文图片 → 在该幻灯片内标注 `（图片来源：姓, 年份）`，并在最后一张幻灯片列出参考文献
- 未使用任何论文图片 → 无需引用，不添加参考文献幻灯片

### 3. 构建 inputText

根据用户需求和检索结果，生成结构化的幻灯片内容草稿。

**格式建议（发给 Gamma 的 inputText）**：

```
# [演示标题]

## 第1张：引言 / 背景
- [要点1]
- [要点2]

## 第2张：[章节标题]
- [要点]
- [数据/引用]
- [图片描述，如有：图示：XXX 示意图（图片来源：Zhang, 2023）]

...（每张一个 ## 块，建议 8-15 张）

## 最后一张：参考文献（仅当使用了论文图片时添加）
- Zhang, 2023
- Smith, 2021
```

**引用格式**：`第一作者姓氏, 年份`（例：`Nielsen, 2016`；中文作者：`张, 2022`）

**textMode 选择**：
- `generate`（默认）：Gamma 基于大纲自由扩展，内容更丰富
- `condense`：Gamma 压缩/精炼输入文本
- `preserve`：尽量保留原始文本，适合内容已很完整时

### 4. 调用 Gamma API

```bash
conda run -n scholaraio python scripts/gamma_ppt.py \
  --text "<inputText内容>" \
  --title "<演示标题>" \
  --mode generate \
  --cards <张数> \
  --lang zh-CN \
  [--export]
```

> **注意**：`--text` 内容若包含换行和引号，建议先写入临时文件再读取，避免 shell 转义问题：
> ```bash
> # 将 inputText 写入临时文件
> # 然后用 Python 读文件方式调用
> conda run -n scholaraio python - <<'PYEOF'
> import subprocess, pathlib
> text = pathlib.Path("workspace/tmp_ppt_input.txt").read_text(encoding="utf-8")
> subprocess.run(["python", "scripts/gamma_ppt.py",
>     "--text", text, "--title", "标题", "--lang", "zh-CN"], check=True)
> PYEOF
> ```

### 5. 返回结果

脚本输出包含：
- **Gamma URL**：在线演示地址（可直接分享/编辑）
- **PPTX URL**（若加了 `--export`）：下载链接
- **Generation ID**：用于后续查询

向用户展示链接，说明：
- 在 Gamma 网页可直接编辑、修改主题风格、调整布局
- PPTX 链接有效期有限，需及时下载

## 常见场景

| 场景 | 建议操作 |
|------|---------|
| 学术报告（给导师/组会） | mode=preserve，内容详实，cards=12-15 |
| 会议 Poster 介绍 | mode=condense，精炼要点，cards=8-10 |
| 文献综述汇报 | 先 /literature-review 生成综述，再用综述内容做 PPT |
| 快速主题介绍 | mode=generate，提供大纲，Gamma 自动扩展 |

## 错误处理

- **401 Unauthorized**：检查 `config.local.yaml` 中 `gamma.api_key` 是否正确
- **连接超时（ConnectTimeout）**：Gamma API 需要代理。在 `workspace/run_gamma.py` 中设置 `os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10080"`（端口以实际为准）
- **生成超时**：Gamma 通常 1-3 分钟完成；网络问题时重试
- **conda GBK 编码错误**：将 inputText 写入 `workspace/tmp_ppt_input.txt`，再通过 `workspace/run_gamma.py` 包装脚本调用（不要用 `conda run -n scholaraio python -c "..."` 多行方式）
- **API 返回 400（invalid params）**：`language` 和 `title` 字段不被 Gamma API 支持，已从脚本中移除
