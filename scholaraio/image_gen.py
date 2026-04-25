"""
image_gen.py — AI 图片生成模块
================================

支持两种后端（均通过 VectorEngine 中转）：

  native  — Gemini 原生格式，POST /v1beta/models/{model}:generateContent
            响应为 base64 内联图片，支持宽高比控制
  chat    — OpenAI chat 兼容格式，POST /v1/chat/completions
            与现有 LLM 后端同协议，响应解析更简单

用法
----
    from scholaraio.config import load_config
    from scholaraio.image_gen import generate_image

    cfg = load_config()
    path = generate_image("a neural network diagram", cfg)
    print(f"图片已保存: {path}")
"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from scholaraio.config import Config

_log = logging.getLogger(__name__)

# Supported aspect ratios for native Gemini format
ASPECT_RATIOS = {"1:1", "4:3", "3:4", "16:9", "9:16"}

# Default model for each backend
_DEFAULT_MODEL_NATIVE = "gemini-2.5-flash-image"
_DEFAULT_MODEL_CHAT = "gemini-2.0-flash-exp-image-generation"


def generate_image(
    prompt: str,
    cfg: "Config",
    *,
    output_path: Path | None = None,
    aspect_ratio: str | None = None,
) -> Path:
    """根据文本描述生成图片并保存到文件。

    Args:
        prompt: 图片描述（中文或英文均可）。
        cfg: ScholarAIO 配置对象。
        output_path: 保存路径。为 ``None`` 时自动生成 ``workspace/images/<timestamp>.png``。
        aspect_ratio: 宽高比（仅 native 格式有效），如 ``"16:9"``、``"1:1"``。
            不指定则使用模型默认值（通常 1:1）。

    Returns:
        保存后的图片文件绝对路径。

    Raises:
        ValueError: API 返回无法解析的响应或未找到图片数据。
        requests.HTTPError: API 请求失败（HTTP 非 2xx）。
    """
    image_cfg = cfg.image_gen
    backend = image_cfg.format

    if output_path is None:
        out_dir = cfg._root / image_cfg.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = out_dir / f"{ts}.png"

    if backend == "chat":
        return _generate_chat(prompt, cfg, output_path)
    else:
        return _generate_native(prompt, cfg, output_path, aspect_ratio=aspect_ratio)


def _generate_native(
    prompt: str,
    cfg: "Config",
    output_path: Path,
    aspect_ratio: str | None = None,
) -> Path:
    """使用 Gemini 原生格式生成图片。

    POST /v1beta/models/{model}:generateContent
    响应中图片以 base64 内联数据形式返回。
    """
    image_cfg = cfg.image_gen
    model = image_cfg.model or _DEFAULT_MODEL_NATIVE
    api_key = _resolve_api_key(cfg)
    base_url = image_cfg.base_url.rstrip("/")

    url = f"{base_url}/v1beta/models/{model}:generateContent"

    generation_config: dict = {
        "responseModalities": ["IMAGE"],
    }
    if aspect_ratio and aspect_ratio in ASPECT_RATIOS:
        generation_config["aspectRatio"] = aspect_ratio

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": generation_config,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    _log.debug("Image gen (native) → %s | model=%s", url, model)
    t0 = time.monotonic()

    resp = requests.post(url, json=payload, headers=headers, timeout=image_cfg.timeout)
    resp.raise_for_status()
    data = resp.json()

    elapsed = round(time.monotonic() - t0, 1)
    _log.debug("Image gen done in %.1fs", elapsed)

    # Parse response: candidates[].content.parts[].inlineData
    image_bytes = _extract_image_native(data)
    output_path.write_bytes(image_bytes)
    _log.debug("Saved image: %s", output_path)
    return output_path.resolve()


def _generate_chat(
    prompt: str,
    cfg: "Config",
    output_path: Path,
) -> Path:
    """使用 OpenAI chat 兼容格式生成图片。

    POST /v1/chat/completions，model = gemini-2.0-flash-exp-image-generation
    图片以 data:image/...;base64,... 格式内嵌在响应内容中。
    """
    image_cfg = cfg.image_gen
    model = image_cfg.model or _DEFAULT_MODEL_CHAT
    api_key = _resolve_api_key(cfg)
    base_url = image_cfg.base_url.rstrip("/")

    url = f"{base_url}/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    _log.debug("Image gen (chat) → %s | model=%s", url, model)
    t0 = time.monotonic()

    resp = requests.post(url, json=payload, headers=headers, timeout=image_cfg.timeout)
    resp.raise_for_status()
    data = resp.json()

    elapsed = round(time.monotonic() - t0, 1)
    _log.debug("Image gen done in %.1fs", elapsed)

    image_bytes = _extract_image_chat(data)
    output_path.write_bytes(image_bytes)
    _log.debug("Saved image: %s", output_path)
    return output_path.resolve()


# ============================================================================
#  Response parsers
# ============================================================================


def _extract_image_native(data: dict) -> bytes:
    """从 Gemini 原生响应中提取 base64 图片并解码。

    Args:
        data: API 返回的 JSON 字典。

    Returns:
        图片的原始字节数据。

    Raises:
        ValueError: 响应中未找到图片数据。
    """
    candidates = data.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        for part in parts:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline:
                b64 = inline.get("data", "")
                if b64:
                    return base64.b64decode(b64)
    raise ValueError(
        f"未在响应中找到图片数据。响应摘要: {str(data)[:300]}"
    )


def _extract_image_chat(data: dict) -> bytes:
    """从 OpenAI chat 响应中提取 base64 图片并解码。

    支持两种格式：
    - content 为字符串（包含 data:image/...;base64,... 格式）
    - content 为列表（多模态 content block，含 image_url 或 inline_data）

    Args:
        data: API 返回的 JSON 字典。

    Returns:
        图片的原始字节数据。

    Raises:
        ValueError: 响应中未找到图片数据。
    """
    try:
        choices = data["choices"]
    except (KeyError, TypeError) as e:
        raise ValueError(f"响应结构异常: {e}\n{str(data)[:300]}") from e

    for choice in choices:
        message = choice.get("message") or {}
        content = message.get("content")

        if isinstance(content, str):
            b64 = _parse_data_uri(content)
            if b64:
                return base64.b64decode(b64)

        elif isinstance(content, list):
            for block in content:
                # OpenAI image_url format
                if block.get("type") == "image_url":
                    url = (block.get("image_url") or {}).get("url", "")
                    b64 = _parse_data_uri(url)
                    if b64:
                        return base64.b64decode(b64)
                # Gemini inline_data format in chat response
                elif block.get("type") in ("image", "inline_data"):
                    inline = block.get("image") or block.get("inline_data") or {}
                    b64 = inline.get("data", "")
                    if b64:
                        return base64.b64decode(b64)

    raise ValueError(
        f"未在 chat 响应中找到图片数据。响应摘要: {str(data)[:300]}"
    )


def _parse_data_uri(uri: str) -> str | None:
    """从 data URI 提取 base64 数据部分。

    Args:
        uri: 形如 ``data:image/png;base64,<data>`` 的字符串。

    Returns:
        base64 字符串，或 ``None``（非 data URI）。
    """
    if uri.startswith("data:") and ";base64," in uri:
        return uri.split(";base64,", 1)[1]
    return None


def _resolve_api_key(cfg: "Config") -> str:
    """按优先级查找图片生成 API key。

    查找顺序:
    1. ``config.local.yaml`` 中的 ``image_gen.api_key``
    2. 环境变量 ``VECTORENGINE_API_KEY``
    3. 环境变量 ``IMAGE_GEN_API_KEY``
    4. 回退到 LLM API key（``cfg.resolved_api_key()``）

    Args:
        cfg: ScholarAIO 配置对象。

    Returns:
        API key 字符串，未找到则返回空字符串。
    """
    import os
    if cfg.image_gen.api_key:
        return cfg.image_gen.api_key
    for env_var in ("VECTORENGINE_API_KEY", "IMAGE_GEN_API_KEY"):
        val = os.environ.get(env_var, "")
        if val:
            return val
    # Fall back to LLM key (useful if using the same provider)
    return cfg.resolved_api_key()
