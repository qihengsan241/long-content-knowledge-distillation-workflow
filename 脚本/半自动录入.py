from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from 核心模块.导出器 import export_json, export_markdown, export_obsidian_copy
from 核心模块.数据结构 import TranscriptDocument
from 核心模块.工具路由 import ToolRoute, route_tool
from 核心模块.文本清洗 import clean_pasted_text
from 核心模块.时间戳识别 import parse_pasted_text
from 生成最终提示词 import DEFAULT_PROMPT, build_final_prompt


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "输出"
DEFAULT_FINAL_PROMPT = DEFAULT_OUTPUT_DIR / "最终提示词.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="半自动录入第三方工具提取出的字幕、逐字稿或正文。")
    parser.add_argument("--链接", default="", help="原始视频、文章或网页链接。未提供时会交互式询问。")
    parser.add_argument("--标题", default="", help="可选：输出标题。默认按平台生成。")
    parser.add_argument("--输出目录", default=str(DEFAULT_OUTPUT_DIR), help="输出目录，默认：输出/。")
    parser.add_argument("--文件名前缀", default="逐字稿", help="输出文件名前缀，默认：逐字稿。")
    parser.add_argument("--提示词", default=str(DEFAULT_PROMPT), help="知识脱水 Prompt 文件。")
    parser.add_argument("--黑曜石规则", default="", help="可选：黑曜石输出规则文件。")
    parser.add_argument("--最终提示词", default=str(DEFAULT_FINAL_PROMPT), help="最终提示词输出路径。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source_url = args.链接.strip() or input("请输入原始链接：").strip()
        route = route_tool(source_url)
        print_tool_route(route)

        print("")
        print("请把第三方工具提取出的字幕、逐字稿或正文粘贴到这里。")
        print("粘贴完成后，单独输入一行 END 结束。")
        pasted_text = read_until_end()
        cleaned_text = clean_pasted_text(pasted_text)
        if not cleaned_text:
            raise ValueError("没有收到有效文本，不能进入知识脱水流程。")

        segments, has_timestamps, warnings = parse_pasted_text(cleaned_text)
        document = TranscriptDocument(
            source_url=source_url,
            platform=route.platform,
            title=args.标题.strip() or f"{route.platform} 半自动录入",
            has_timestamps=has_timestamps,
            segments=segments,
            raw_text="\n".join(segment.text for segment in segments if segment.text.strip()),
            extraction_method=f"manual-paste:{route.kind}",
            warnings=warnings,
        )
        document.assert_has_content()

        output_dir = Path(args.输出目录)
        prefix = args.文件名前缀
        json_path = export_json(document, output_dir / f"{prefix}.json")
        markdown_path = export_markdown(document, output_dir / f"{prefix}.md")
        obsidian_path = export_obsidian_copy(document, output_dir / f"{prefix}_黑曜石复制.md")
        final_prompt_path = build_final_prompt(
            transcript_path=markdown_path,
            prompt_path=Path(args.提示词),
            output_path=Path(args.最终提示词),
            obsidian_rules_path=Path(args.黑曜石规则) if args.黑曜石规则 else None,
        )

        print("")
        print(f"是否有时间戳：{str(has_timestamps).lower()}")
        if warnings:
            print(f"警告信息：{'；'.join(warnings)}")
        print(f"已输出标准逐字稿 JSON：{json_path}")
        print(f"已输出标准逐字稿 Markdown：{markdown_path}")
        print(f"已输出可复制到黑曜石的 Markdown：{obsidian_path}")
        print(f"已生成最终提示词：{final_prompt_path}")
        return 0
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"半自动录入失败：{exc}", file=sys.stderr)
        return 1


def print_tool_route(route: ToolRoute) -> None:
    print("")
    print(f"平台识别：{route.platform}")
    print("工具建议：")
    for index, suggestion in enumerate(route.suggestions, start=1):
        print(f"{index}. {suggestion}")
    if route.resource_files:
        print("可参考说明：")
        for resource_file in route.resource_files:
            print(f"- {resource_file}")


def read_until_end() -> str:
    lines: list[str] = []
    while True:
        line = sys.stdin.readline()
        if line == "":
            break
        if line.rstrip("\n\r").strip() == "END":
            break
        lines.append(line)
    return "".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

