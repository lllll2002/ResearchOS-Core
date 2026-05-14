from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
import json
import re
import time

from _common import append_wrapper_event, get_env, load_config, wrapper_event_path

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent.parent.parent / "workspace" / "current_task" / "20_translation.md"


class TranslationError(Exception):
    pass


def read_source_file(file_path: str) -> str:
    """读取源论文文件内容"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def split_paper_into_sections(content: str, max_section_length: int = 4000) -> list[str]:
    """将论文分割成适合API调用的章节"""
    sections = []
    current_section = ""
    current_length = 0

    # 按主要章节分割（以 # 开头的标题）
    lines = content.split('\n')
    current_section_lines = []

    for line in lines:
        # 检查是否是新章节标题
        if line.startswith('#') and current_section_lines:
            # 保存当前章节
            current_section = '\n'.join(current_section_lines)
            sections.append(current_section)
            current_section_lines = [line]
            current_length = 0
        else:
            # 检查加入此行后是否会超过最大长度
            line_length = len(line.encode('utf-8'))
            if current_length + line_length > max_section_length:
                # 如果超过，先保存当前章节
                if current_section_lines:
                    current_section = '\n'.join(current_section_lines)
                    sections.append(current_section)
                    current_section_lines = [line]
                    current_length = line_length
                else:
                    # 单行太长，需要分割
                    current_section_lines.append(line)
                    current_section = '\n'.join(current_section_lines)
                    sections.append(current_section)
                    current_section_lines = []
                    current_length = 0
            else:
                current_section_lines.append(line)
                current_length += line_length

    # 添加最后一个章节
    if current_section_lines:
        current_section = '\n'.join(current_section_lines)
        sections.append(current_section)

    return sections


def create_translation_prompt(section: str, section_num: int, total_sections: int) -> str:
    """创建翻译提示词"""
    return f"""你是专业的学术论文翻译专家，精通物理学、生物学和材料科学领域的术语翻译。

任务：将以下学术论文章节翻译成中文。

翻译要求：
1. 保持学术严谨性和术语准确性
2. 完整保留所有 LaTeX 数学公式（包括 $...$ 和 $$...$$ 格式）
3. 图片占位符保持原样（如 ![](images/...)）
4. 保持原文的层级结构（# ## ###）
5. 专业术语采用标准中文科学翻译
6. 保持原文的引用格式（如 [1, 2]）
7. 保持表格格式完整
8. 翻译后的代码块保持原语言（如Python代码）

待翻译章节（第 {section_num}/{total_sections} 部分）：

{section}"""


def call_deepseek_translate(url: str, api_key: str, model: str, prompt: str, temperature: float, max_tokens: int) -> tuple[str, dict]:
    """调用 DeepSeek API 进行翻译"""
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise TranslationError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise TranslationError(str(exc)) from exc

    try:
        content = body["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise TranslationError(f"Unexpected response shape: {body}") from exc

    # 提取使用量
    usage = body.get("usage", {})
    usage_info = {
        "tokens_in": usage.get("prompt_tokens"),
        "tokens_out": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "usage_source": "api" if usage else None,
    }

    return content, usage_info


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(description="使用 DeepSeek API 翻译学术论文")
    parser.add_argument("--input", required=True, help="输入论文文件路径")
    parser.add_argument("--output", required=True, help="输出翻译文件路径")
    parser.add_argument("--model", default="deepseek-chat", help="DeepSeek 模型名称")
    parser.add_argument("--temperature", type=float, default=0.3, help="温度参数")
    parser.add_argument("--max-tokens", type=int, default=8000, help="最大 token 数")
    parser.add_argument("--max-section-length", type=int, default=4000, help="每章最大字符数")
    parser.add_argument("--dry-run", action="store_true", help="干运行，不实际调用 API")

    args = parser.parse_args()

    # 验证输入文件
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"开始翻译论文: {input_path}")
    print(f"输出文件: {output_path}")

    # 读取源文件
    try:
        content = read_source_file(input_path)
    except Exception as exc:
        print(f"读取输入文件失败: {exc}", file=sys.stderr)
        return 1

    # 分割论文
    print(f"分割论文为多个章节 (每章最大 {args.max_section_length} 字符)...")
    sections = split_paper_into_sections(content, args.max_section_length)
    total_sections = len(sections)
    print(f"共 {total_sections} 个章节需要翻译")

    # 设置 API 配置
    api_base = "https://api.deepseek.com/v1/chat/completions"
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY environment variable not set")
        sys.exit(1)

    if args.dry_run:
        print("干运行模式 - 不会实际调用 API")
        print(f"将要翻译 {total_sections} 个章节")
        return 0

    # 创建事件文件
    event_file = wrapper_event_path("deepseek_translate")

    # 翻译每个章节并逐章写入
    translated_sections = []
    failed_sections = []

    for i, section in enumerate(sections, 1):
        print(f"\n处理第 {i}/{total_sections} 章节...")
        section_length = len(section.encode('utf-8'))
        print(f"  章节长度: {section_length} 字节")

        # 创建翻译提示词
        prompt = create_translation_prompt(section, i, total_sections)

        try:
            # 调用 DeepSeek API
            append_wrapper_event(event_file, "translate.started", {
                "section": i,
                "total_sections": total_sections,
                "section_length": section_length
            })

            translated, usage = call_deepseek_translate(
                api_base,
                api_key,
                args.model,
                prompt,
                args.temperature,
                args.max_tokens
            )

            print(f"  翻译完成 (输入: {usage['tokens_in']} tokens, 输出: {usage['tokens_out']} tokens)")
            translated_sections.append(translated)

            append_wrapper_event(event_file, "translate.completed", {
                "section": i,
                "tokens_in": usage['tokens_in'],
                "tokens_out": usage['tokens_out'],
                "total_tokens": usage['total_tokens']
            })

            # 实时写入已完成的章节
            if translated_sections:
                partial_translation = "\n\n".join(translated_sections)
                try:
                    output_path.write_text(partial_translation, encoding='utf-8')
                    print(f"  实时保存: 已完成 {len(translated_sections)} 章节")
                except Exception as exc:
                    print(f"  写入失败: {exc}", file=sys.stderr)

            # 避免触发 API 速率限制
            if i < total_sections:
                time.sleep(1)  # 减少延迟时间

        except TranslationError as exc:
            print(f"  翻译失败: {exc}")
            failed_sections.append(i)
            append_wrapper_event(event_file, "translate.failed", {
                "section": i,
                "error": str(exc)
            })

        except KeyboardInterrupt:
            print("\n翻译被用户中断")
            # 中断时也要保存已完成的翻译
            if translated_sections:
                partial_translation = "\n\n".join(translated_sections)
                try:
                    output_path.write_text(partial_translation, encoding='utf-8')
                    print(f"  中断保存: 已完成 {len(translated_sections)} 章节")
                except Exception as exc:
                    print(f"  写入失败: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"  未预期的错误: {exc}")
            import traceback
            traceback.print_exc()
            return 1

    # 最终合并并写入完整翻译
    full_translation = "\n\n".join(translated_sections)

    try:
        output_path.write_text(full_translation, encoding='utf-8')
        print(f"\n✅ 翻译完成！结果已保存到: {output_path}")
    except Exception as exc:
        print(f"写入输出文件失败: {exc}", file=sys.stderr)
        return 1

    # 总结报告
    print(f"\n翻译统计:")
    print(f"  总章节数: {total_sections}")
    print(f"  成功翻译: {len(translated_sections)}")
    print(f"  失败章节: {len(failed_sections)}")
    if failed_sections:
        print(f"  失败章节编号: {failed_sections}")

    return 0 if not failed_sections else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TranslationError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
