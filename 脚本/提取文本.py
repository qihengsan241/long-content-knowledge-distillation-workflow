from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from 核心模块.导出器 import export_json, export_markdown, export_obsidian_copy
from 核心模块.平台路由 import SourceRoute, route_input
from 核心模块.标准化 import document_from_raw_text, document_from_subtitle_file, document_from_text_file
from 核心模块.适配器 import ExtractionNotAvailableError
from 提取器.B站 import BilibiliExtractor
from 提取器.小红书 import XiaohongshuExtractor
from 提取器.抖音 import DouyinExtractor
from 提取器.文章 import ArticleExtractor
from 提取器.油管 import YouTubeExtractor
from 提取器.音频 import AudioExtractor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="提取文本/逐字稿并导出为标准 JSON 与 Markdown。")
    parser.add_argument("输入", help="URL、本地字幕文件、本地转录稿，或长篇文章文本。")
    parser.add_argument("--输出目录", default=str(PROJECT_ROOT / "输出"), help="输出目录，默认是项目内的 输出/。")
    parser.add_argument("--文件名前缀", default="逐字稿", help="输出文件名前缀，默认：逐字稿。")
    parser.add_argument("--语言", default="zh-Hans,zh-CN,zh,zh-TW,en", help="YouTube 字幕语言优先级，逗号分隔。")
    parser.add_argument("--禁用自动字幕", action="store_true", help="YouTube 只使用人工字幕，不使用自动字幕。")
    parser.add_argument("--仅识别平台", action="store_true", help="只打印平台识别结果，不执行提取。")
    return parser


def extract_by_route(route: SourceRoute, language_preferences: list[str], allow_auto_captions: bool):
    if route.kind == "youtube":
        return YouTubeExtractor(language_preferences, allow_auto_captions=allow_auto_captions).extract(route.input_value)
    if route.kind == "bilibili":
        return BilibiliExtractor().extract(route.input_value)
    if route.kind == "douyin":
        return DouyinExtractor().extract(route.input_value)
    if route.kind == "xiaohongshu":
        return XiaohongshuExtractor().extract(route.input_value)
    if route.kind == "audio":
        return AudioExtractor().extract(route.input_value)
    if route.kind == "article":
        return ArticleExtractor().extract(route.input_value)
    if route.kind == "local_subtitle" and route.path:
        return document_from_subtitle_file(route.path)
    if route.kind in {"local_transcript", "local_text"} and route.path:
        return document_from_text_file(route.path)
    if route.kind == "raw_text":
        return document_from_raw_text(route.input_value)
    raise ExtractionNotAvailableError(f"暂不支持的输入类型：{route.kind}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        route = route_input(args.输入)
        print(f"平台识别：{route.platform}（{route.reason}）")
        if args.仅识别平台:
            return 0

        language_preferences = [item.strip() for item in args.语言.split(",") if item.strip()]
        document = extract_by_route(route, language_preferences, allow_auto_captions=not args.禁用自动字幕)
        document.assert_has_content()

        output_dir = Path(args.输出目录)
        prefix = args.文件名前缀
        json_path = export_json(document, output_dir / f"{prefix}.json")
        markdown_path = export_markdown(document, output_dir / f"{prefix}.md")
        obsidian_path = export_obsidian_copy(document, output_dir / f"{prefix}_黑曜石复制.md")

        print(f"已输出标准逐字稿 JSON：{json_path}")
        print(f"已输出标准逐字稿 Markdown：{markdown_path}")
        print(f"已输出可复制到黑曜石的 Markdown：{obsidian_path}")
        return 0
    except ExtractionNotAvailableError as exc:
        print(f"提取失败：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

