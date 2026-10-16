from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from 核心模块.导出器 import export_json, export_markdown
from 核心模块.适配器 import ExtractionNotAvailableError
from 提取器.YouTube字幕 import YouTubeTranscriptExtractor


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "输出"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="使用 youtube-transcript-api 提取 YouTube 字幕并导出标准逐字稿。")
    parser.add_argument("链接", help="YouTube 链接或 video id。")
    parser.add_argument("--语言", default="zh-Hans,zh-CN,zh,zh-TW,en", help="字幕语言优先级，逗号分隔。")
    parser.add_argument("--输出目录", default=str(DEFAULT_OUTPUT_DIR), help="输出目录，默认：输出/。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        languages = [item.strip() for item in args.语言.split(",") if item.strip()]
        document = YouTubeTranscriptExtractor(languages).extract(args.链接)
        output_dir = Path(args.输出目录)
        markdown_path = export_markdown(document, output_dir / "逐字稿.md")
        json_path = export_json(document, output_dir / "逐字稿.json")
        print("是否有时间戳：true")
        print(f"提取方式：{document.extraction_method}")
        print(f"已生成：{markdown_path}")
        print(f"已生成：{json_path}")
        return 0
    except ExtractionNotAvailableError as exc:
        print(f"YouTube 字幕提取失败：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

