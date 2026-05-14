---
name: draw
description: 调用 Gemini（via VectorEngine）生成图片，保存到 workspace/images/。支持自然语言描述、宽高比控制、图片编辑。
triggers:
  - "生成图片"
  - "画一张"
  - "画一个"
  - "绘制"
  - "生成示意图"
  - "生成流程图"
  - "generate image"
  - "draw"
  - "create image"
  - "visualize"
---

# 图片生成

调用 Gemini 图片生成模型，将自然语言描述转换为图片，保存到 `workspace/images/`。

## CLI 命令

```bash
# 基本用法（native 格式，gemini-2.5-flash-image）
scholaraio draw <提示词>

# 指定宽高比
scholaraio draw <提示词> --aspect 16:9

# 指定保存路径
scholaraio draw <提示词> --output workspace/images/my_diagram.png

# 使用 chat 兼容格式（gemini-2.0-flash-exp-image-generation）
scholaraio draw <提示词> --format chat

# 指定模型
scholaraio draw <提示词> --model gemini-2.5-flash-image

# 示例：生成神经网络示意图
scholaraio draw "a clear diagram of transformer architecture with attention mechanism" --aspect 16:9

# 示例：生成研究流程图
scholaraio draw "flowchart of a machine learning pipeline: data collection, preprocessing, model training, evaluation, deployment" --aspect 4:3
```

## 支持的宽高比（--aspect）

| 值 | 用途 |
|----|------|
| `1:1` | 方形（默认） |
| `16:9` | 宽屏横图，适合流程图 |
| `9:16` | 竖图 |
| `4:3` | 传统屏幕比例 |
| `3:4` | 竖版 |

## 配置

在 `config.local.yaml` 中配置：

```yaml
image_gen:
  api_key: "your-vectorengine-api-key"
  base_url: https://api.vectorengine.ai
  format: native          # native（Gemini 原生）| chat（OpenAI 兼容）
  model: ""               # 留空自动选择
  output_dir: workspace/images
  timeout: 120
```

API key 也可通过环境变量设置：`VECTORENGINE_API_KEY` 或 `IMAGE_GEN_API_KEY`。
如未单独配置，自动回退到 LLM 的 `api_key`。

## 执行逻辑

1. 理解用户意图，将请求转化为英文提示词（Gemini 对英文提示词效果更好）
2. 调用 `scholaraio draw <prompt>` 生成图片
3. 图片保存到 `workspace/images/<timestamp>.png`
4. 用 Read 工具读取图片展示给用户，并说明保存路径
5. 根据用户反馈可调整提示词重新生成

## 提示词技巧

- **科学图表**：在提示词中说明是 "scientific diagram"、"schematic"、"flowchart"，并描述图的组件和连接关系
- **风格控制**：加入 "clean white background"、"minimal style"、"professional illustration" 等
- **内容精确**：列出图中需要包含的关键元素，用逗号分隔
- **避免文字歧义**：如果图中需要英文标签，在提示词中明确说明

## 示例场景

用户说："帮我画一张 Transformer 架构图"
→ 翻译为英文提示词，调用 `scholaraio draw "Transformer architecture diagram showing encoder-decoder structure with multi-head self-attention, feed-forward layers, positional encoding, clean scientific illustration style" --aspect 16:9`
→ Read 工具读取图片展示
→ 说明保存路径

用户说："生成一张研究方法流程图"
→ 先询问流程图包含哪些步骤
→ 根据回答生成提示词并调用 draw
