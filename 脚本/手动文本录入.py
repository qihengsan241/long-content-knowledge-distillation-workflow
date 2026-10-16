from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from 核心模块.导出器 import export_json, export_markdown
from 核心模块.数据结构 import TranscriptDocument
from 核心模块.文本清洗 import clean_pasted_text
from 核心模块.时间戳识别 import parse_pasted_text


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "输出"
SOURCE_TYPES = [
    "视频字幕",
    "播客转录稿",
    "长篇文章",
    "访谈记录",
    "课程文稿",
    "带时间戳文本",
    "不带时间戳文本",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="手动粘贴原始文本、字幕或转录稿，并标准化为逐字稿文件。")
    parser.add_argument("--类型", default="", help="内容来源类型。")
    parser.add_argument("--标题", default="", help="来源标题。")
    parser.add_argument("--来源链接", default="", help="来源链接，可为空。")
    parser.add_argument("--作者", default="", help="作者，可为空。")
    parser.add_argument("--平台", default="", help="平台，可为空。")
    parser.add_argument("--输出目录", default=str(DEFAULT_OUTPUT_DIR), help="输出目录，默认：输出/。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source_type = args.类型.strip() or ask_source_type()
        title = args.标题.strip() or input("请输入来源标题：").strip()
        source_url = args.来源链接.strip() or input("请输入来源链接（可为空）：").strip()
        author = args.作者.strip() or input("请输入作者（可为空）：").strip()
        platform = args.平台.strip() or input("请输入平台（可为空）：").strip()

        print("")
        print("请粘贴全文。粘贴完成后，单独输入一行 END 结束。")
        pasted_text = read_until_end()
        cleaned_text = clean_pasted_text(pasted_text)
        if not cleaned_text:
            raise ValueError("没有收到有效文本，不能生成逐字稿。")

        segments, has_timestamps, warnings = parse_pasted_text(cleaned_text)
        document = TranscriptDocument(
            source_url=source_url,
            platform=platform or source_type,
            title=title or "手动录入文本",
            author=author,
            has_timestamps=has_timestamps,
            segments=segments,
            raw_text=cleaned_text,
            extraction_method=f"manual-input:{source_type}",
            warnings=warnings,
        )
        document.assert_has_content()

        output_dir = Path(args.输出目录)
        json_path = export_json(document, output_dir / "逐字稿.json")
        markdown_path = export_markdown(document, output_dir / "逐字稿.md")
        print("")
        print(f"是否有时间戳：{str(has_timestamps).lower()}")
        if warnings:
            print(f"警告信息：{'；'.join(warnings)}")
        print(f"已生成：{markdown_path}")
        print(f"已生成：{json_path}")
        return 0
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"手动文本录入失败：{exc}", file=sys.stderr)
        return 1


def ask_source_type() -> str:
    print("请选择内容来源类型：")
    for index, source_type in enumerate(SOURCE_TYPES, start=1):
        print(f"{index}. {source_type}")
    choice = input("输入序号或直接输入类型：").strip()
    if choice.isdigit():
        index = int(choice)
        if 1 <= index <= len(SOURCE_TYPES):
            return SOURCE_TYPES[index - 1]
    return choice or "不带时间戳文本"


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

