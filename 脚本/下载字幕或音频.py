from __future__ import annotations

import argparse
from datetime import datetime
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from 核心模块.导出器 import export_json, export_markdown
from 核心模块.适配器 import ExtractionNotAvailableError
from 提取器.媒体下载 import MediaDownloader


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "输出"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="使用 yt-dlp 优先提取字幕；没有字幕时下载音频到 输出/音频/。")
    parser.add_argument("链接", help="视频链接。")
    parser.add_argument("--语言", default="zh-Hans,zh-CN,zh,zh-TW,en", help="字幕语言优先级，逗号分隔。")
    parser.add_argument("--输出目录", default=str(DEFAULT_OUTPUT_DIR), help="输出目录，默认：输出/。")
    parser.add_argument("--cookies-from-browser", choices=["chrome", "edge", "firefox"], default="", help="明确授权后读取本机浏览器 Cookie。")
    parser.add_argument("--cookies-file", default="", help="手动提供 cookie.txt 文件路径，仅本次调用使用。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        languages = [item.strip() for item in args.语言.split(",") if item.strip()]
        output_dir = Path(args.输出目录)
        result = MediaDownloader(
            output_dir,
            languages,
            cookies_from_browser=args.cookies_from_browser,
            cookies_file=args.cookies_file or None,
        ).extract_subtitle_or_download_audio(args.链接)
        if result.cookie_mode and result.cookie_mode != "未启用 Cookie":
            print(f"Cookie 授权：{result.cookie_mode}（未记录 Cookie 内容）")
        if result.document:
            markdown_path = export_markdown(result.document, output_dir / "逐字稿.md")
            json_path = export_json(result.document, output_dir / "逐字稿.json")
            print("已找到字幕并生成标准逐字稿。")
            if result.subtitle_path:
                print(f"原始字幕已保存：{result.subtitle_path}")
            print(f"已生成：{markdown_path}")
            print(f"已生成：{json_path}")
            return 0
        if result.audio_path:
            print("没有找到可用字幕，已下载音频。")
            print(f"音频文件：{result.audio_path}")
            print("下一步可运行：python 脚本/转写音频.py \"音频文件路径\"")
            return 0
        raise ExtractionNotAvailableError("没有生成字幕或音频。")
    except ExtractionNotAvailableError as exc:
        write_failure_report(Path(args.输出目录) / "媒体下载失败报告.md", args, exc)
        print(f"下载字幕或音频失败：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        write_failure_report(Path(args.输出目录) / "媒体下载失败报告.md", args, exc)
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1


def write_failure_report(path: Path, args: argparse.Namespace, error: Exception) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cookie_mode = "未启用 Cookie"
    if args.cookies_from_browser:
        cookie_mode = f"浏览器 Cookie 模式：{args.cookies_from_browser}"
    elif args.cookies_file:
        cookie_mode = "Cookie 文件模式"
    lines = [
        "# 媒体下载失败报告",
        "",
        f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"链接：{args.链接}",
        f"Cookie 授权：{cookie_mode}",
        f"错误类型：{error.__class__.__name__}",
        f"错误信息：{error}",
        "",
        "## 安全说明",
        "",
        "- 本报告不记录 Cookie 内容。",
        "- Cookie 只应用于用户明确授权并有权限访问的视频。",
        "- 如果使用 cookie.txt，用完后可以删除。",
        "",
        "## 下一步建议",
        "",
        "- 如果提示 fresh cookies，可以在确认安全风险后使用 `--cookies-from-browser chrome/edge/firefox`。",
        "- 或手动提供 `--cookies-file cookie.txt`。",
        "- 如果仍失败，请改用本地视频/音频兜底，再走 OCR 或音频转写。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
