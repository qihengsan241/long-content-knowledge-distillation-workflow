from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from 核心模块.导出器 import export_json, export_markdown
from 核心模块.数据结构 import TranscriptDocument
from 核心模块.标准化 import document_from_subtitle_file
from 核心模块.文本清洗 import clean_pasted_text
from 核心模块.时间戳识别 import parse_pasted_text


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "输出"
SUPPORTED_SUFFIXES = {".txt", ".md", ".srt", ".vtt"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="导入本地 .txt/.md/.srt/.vtt 文件，并标准化为逐字稿文件。")
    parser.add_argument("文件", help="本地文本、Markdown、SRT 或 VTT 文件路径。")
    parser.add_argument("--标题", default="", help="可选：来源标题，默认使用文件名。")
    parser.add_argument("--来源链接", default="", help="可选：来源链接。")
    parser.add_argument("--作者", default="", help="可选：作者。")
    parser.add_argument("--平台", default="", help="可选：平台。")
    parser.add_argument("--类型", default="", help="可选：内容类型。")
    parser.add_argument("--输出目录", default=str(DEFAULT_OUTPUT_DIR), help="输出目录，默认：输出/。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        path = Path(args.文件)
        if not path.exists():
            raise FileNotFoundError(f"找不到文件：{path}")
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ValueError("只支持 .txt / .md / .srt / .vtt 文件。")

        document = build_document_from_file(path, args)
        document.assert_has_content()

        output_dir = Path(args.输出目录)
        json_path = export_json(document, output_dir / "逐字稿.json")
        markdown_path = export_markdown(document, output_dir / "逐字稿.md")
        print(f"是否有时间戳：{str(document.has_timestamps).lower()}")
        if document.warnings:
            print(f"警告信息：{'；'.join(document.warnings)}")
        print(f"已生成：{markdown_path}")
        print(f"已生成：{json_path}")
        return 0
    except Exception as exc:
        print(f"导入文本文件失败：{exc}", file=sys.stderr)
        return 1


def build_document_from_file(path: Path, args: argparse.Namespace) -> TranscriptDocument:
    suffix = path.suffix.lower()
    if suffix in {".srt", ".vtt"}:
        document = document_from_subtitle_file(path)
        document.extraction_method = f"file-import:{suffix.lstrip('.')}"
        document.warnings = []
    else:
        content = path.read_text(encoding="utf-8-sig")
        cleaned_text = clean_pasted_text(content)
        segments, has_timestamps, warnings = parse_pasted_text(cleaned_text)
        document = TranscriptDocument(
            has_timestamps=has_timestamps,
            segments=segments,
            raw_text=cleaned_text,
            extraction_method=f"file-import:{suffix.lstrip('.')}",
            warnings=warnings,
        )

    document.source_url = args.来源链接.strip() or str(path)
    document.title = args.标题.strip() or path.stem
    document.author = args.作者.strip()
    document.platform = args.平台.strip() or args.类型.strip() or document.platform or "本地文本文件"
    return document


if __name__ == "__main__":
    raise SystemExit(main())

