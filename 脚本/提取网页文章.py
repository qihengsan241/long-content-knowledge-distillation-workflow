from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from 核心模块.导出器 import export_json
from 核心模块.数据结构 import TranscriptDocument
from 核心模块.适配器 import ExtractionNotAvailableError
from 提取器.网页文章 import WebArticleExtractor


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "输出"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="使用 trafilatura 提取网页文章正文并导出标准逐字稿。")
    parser.add_argument("链接", help="网页文章链接。")
    parser.add_argument("--输出目录", default=str(DEFAULT_OUTPUT_DIR), help="输出目录，默认：输出/。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        document = WebArticleExtractor().extract(args.链接)
        output_dir = Path(args.输出目录)
        markdown_path = export_article_markdown(document, output_dir / "逐字稿.md")
        json_path = export_json(document, output_dir / "逐字稿.json")
        print("是否有时间戳：false")
        if document.warnings:
            print(f"警告信息：{'；'.join(document.warnings)}")
        print(f"已生成：{markdown_path}")
        print(f"已生成：{json_path}")
        print("下一步可运行：python 脚本/生成最终提示词.py")
        return 0
    except ExtractionNotAvailableError as exc:
        print(f"网页文章提取失败：{exc}", file=sys.stderr)
        print("建议退回手动流程：复制网页正文到资料/我的测试文本.md，再运行 python 脚本/导入文本文件.py \"资料/我的测试文本.md\"", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1


def export_article_markdown(document: TranscriptDocument, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    published_date = str(getattr(document, "published_date", "") or "")
    lines = [
        f"# {document.title or '网页文章正文'}",
        "",
        f"来源链接：{document.source_url}",
        "平台：网页文章",
        f"作者：{document.author}",
        f"发布时间：{published_date}",
        "是否有时间戳：false",
        f"提取方式：{document.extraction_method}",
    ]
    if document.warnings:
        lines.append(f"警告信息：{'；'.join(document.warnings)}")
    lines.extend(["", "## 正文", ""])
    for index, segment in enumerate(document.segments, start=1):
        lines.append(f"第 {index} 段：{segment.text}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
