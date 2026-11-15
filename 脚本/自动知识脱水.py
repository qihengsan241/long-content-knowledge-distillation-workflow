from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = PROJECT_ROOT / "脚本"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from 核心模块.平台路由 import SourceRoute, route_input
from 核心模块.配置路径 import resolve_env_path


TEXT_SUFFIXES = {".txt", ".md", ".srt", ".vtt"}
MEDIA_SUFFIXES = {".mp3", ".m4a", ".wav", ".webm", ".mp4"}
DOWNLOADED_MEDIA_SUFFIXES = MEDIA_SUFFIXES | {".aac", ".flac", ".ogg", ".opus", ".mkv"}


class WorkflowError(RuntimeError):
    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="输入链接、本地文件或长文本，自动完成逐字稿、DeepSeek 知识脱水和黑曜石 Markdown 输出。"
    )
    parser.add_argument("输入", nargs="?", default="", help="URL、本地文件路径或长文本；也可通过标准输入传入正文。")
    parser.add_argument("--输出目录", default="", help="可选：本次任务输出目录。默认写入 C:/AI/Outputs。")
    parser.add_argument("--env", default=str(resolve_env_path(PROJECT_ROOT)), help="模型配置文件路径。")
    parser.add_argument("--语言", default="zh-Hans,zh-CN,zh,zh-TW,en", help="字幕语言优先级。")
    parser.add_argument("--转写模型", default="small", help="faster-whisper 模型名，默认 small。")
    parser.add_argument(
        "--简约字幕文件",
        "--插件字幕文件",
        dest="简约字幕文件",
        default="",
        help="可选：简约翻译插件导出的 .txt/.md/.srt/.vtt；仅在 YouTube 直读字幕失败后使用。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = Path(args.输出目录) if args.输出目录 else default_output_dir()
    report_lines = [
        "# 自动知识脱水运行报告",
        "",
        f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"输出目录：{output_dir}",
        "",
        "## 阶段记录",
        "",
    ]

    try:
        source = read_source(args.输入)
        route = route_input(source)
        output_dir.mkdir(parents=True, exist_ok=True)
        report_lines.append(f"- 输入识别：{route.platform}；{route.reason}")

        obtain_transcript(route, source, output_dir, args, report_lines)
        transcript_path = output_dir / "逐字稿.md"
        require_nonempty(transcript_path, "获取真实文本")

        run_required(
            "生成最终提示词",
            "生成最终提示词.py",
            ["--输入", transcript_path, "--输出", output_dir / "最终提示词.md"],
            report_lines,
        )
        run_required(
            "模型知识脱水",
            "调用大模型执行知识脱水.py",
            [
                "--env",
                Path(args.env),
                "--输入",
                output_dir / "最终提示词.md",
                "--输出",
                output_dir / "知识脱水结果.md",
                "--日志",
                output_dir / "模型调用日志.md",
            ],
            report_lines,
        )
        require_nonempty(output_dir / "知识脱水结果.md", "模型知识脱水")

        run_required(
            "黑曜石 Markdown 包装",
            "整理为黑曜石文件.py",
            [
                "--输入",
                output_dir / "知识脱水结果.md",
                "--输出",
                output_dir / "黑曜石笔记.md",
                "--来源",
                source_label(route, source),
            ],
            report_lines,
        )
        require_nonempty(output_dir / "黑曜石笔记.md", "黑曜石 Markdown 包装")

        report_lines.extend(
            [
                "",
                "## 结果",
                "",
                "状态：成功",
                f"逐字稿：{output_dir / '逐字稿.md'}",
                f"最终提示词：{output_dir / '最终提示词.md'}",
                f"知识脱水结果：{output_dir / '知识脱水结果.md'}",
                f"黑曜石笔记：{output_dir / '黑曜石笔记.md'}",
            ]
        )
        write_report(output_dir, report_lines)
        print("自动知识脱水完成。")
        print(f"黑曜石笔记：{output_dir / '黑曜石笔记.md'}")
        print(f"本次全部文件：{output_dir}")
        return 0
    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        stage = exc.stage if isinstance(exc, WorkflowError) else "自动流程"
        report_lines.extend(
            [
                "",
                "## 结果",
                "",
                "状态：失败",
                f"失败阶段：{stage}",
                f"错误类型：{exc.__class__.__name__}",
                f"错误信息：{exc}",
                "",
                "没有生成真实逐字稿时，不会继续调用模型。",
            ]
        )
        report_path = write_report(output_dir, report_lines)
        print(f"自动知识脱水失败（{stage}）：{exc}", file=sys.stderr)
        print(f"运行报告：{report_path}", file=sys.stderr)
        return 1


def default_output_dir() -> Path:
    configured = os.getenv("KNOWLEDGE_DISTILLATION_OUTPUT_ROOT", "").strip()
    root = Path(configured) if configured else Path("C:/AI/Outputs/长内容知识脱水工作流/Codex")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return root / f"{stamp}-auto-distillation"


def read_source(argument: str) -> str:
    value = argument.strip()
    if value:
        return value
    if not sys.stdin.isatty():
        value = sys.stdin.read().strip()
    if not value:
        raise WorkflowError("读取输入", "没有收到链接、文件路径或正文。")
    return value


def obtain_transcript(
    route: SourceRoute,
    source: str,
    output_dir: Path,
    args: argparse.Namespace,
    report_lines: list[str],
) -> None:
    if route.path:
        suffix = route.path.suffix.lower()
        if suffix in TEXT_SUFFIXES:
            run_required("导入本地文本", "导入文本文件.py", [route.path, "--输出目录", output_dir], report_lines)
            return
        if suffix == ".json":
            run_required(
                "导入标准逐字稿 JSON",
                "提取文本.py",
                [route.path, "--输出目录", output_dir, "--文件名前缀", "逐字稿"],
                report_lines,
            )
            return
        if suffix in MEDIA_SUFFIXES:
            run_required(
                "转写本地音频/视频",
                "转写音频.py",
                [route.path, "--模型", args.转写模型, "--输出目录", output_dir],
                report_lines,
            )
            return
        raise WorkflowError("识别本地文件", f"暂不支持的本地文件类型：{suffix or '无扩展名'}")

    if route.kind == "raw_text":
        raw_path = output_dir / "原始文本.txt"
        raw_path.write_text(source.strip() + "\n", encoding="utf-8")
        run_required("导入正文", "导入文本文件.py", [raw_path, "--输出目录", output_dir], report_lines)
        return

    if route.kind == "youtube":
        first = run_script(
            "提取YouTube字幕.py",
            [source, "--语言", args.语言, "--输出目录", output_dir],
        )
        record_result("YouTube 字幕提取", first, report_lines)
        if first.returncode == 0 and transcript_ready(output_dir):
            return
        report_lines.append("- 第一层 YouTube 字幕轨直读不可用，进入简约翻译插件层。")

        plugin_subtitle = args.简约字幕文件.strip()
        if plugin_subtitle:
            plugin_path = Path(plugin_subtitle).expanduser()
            if plugin_path.is_file():
                second = run_script(
                    "导入文本文件.py",
                    [
                        plugin_path,
                        "--来源链接",
                        source,
                        "--平台",
                        "YouTube",
                        "--提取方式",
                        "简约翻译插件",
                        "--简约插件清洗",
                        "--输出目录",
                        output_dir,
                    ],
                )
                record_result("简约翻译插件字幕导入", second, report_lines)
                if second.returncode == 0 and transcript_ready(output_dir):
                    return
            else:
                report_lines.append(f"- 简约翻译插件字幕文件不存在：{plugin_path}")
        else:
            report_lines.append(
                "- 未提供简约翻译插件字幕文件；Codex 浏览器协作应在此阶段从页面可见控件下载 VTT。"
            )

        report_lines.append("- 第二层未取得完整字幕，进入 yt-dlp 字幕/音频兜底。")
        obtain_from_media_url(source, output_dir, args, report_lines)
        return

    if route.kind in {"bilibili", "douyin", "xiaohongshu", "audio"}:
        obtain_from_media_url(source, output_dir, args, report_lines)
        return

    if route.kind == "article":
        run_required("提取网页正文", "提取网页文章.py", [source, "--输出目录", output_dir], report_lines)
        return

    raise WorkflowError("获取文本", f"暂不支持的输入类型：{route.kind}")


def obtain_from_media_url(
    source: str,
    output_dir: Path,
    args: argparse.Namespace,
    report_lines: list[str],
) -> None:
    result = run_script(
        "下载字幕或音频.py",
        [source, "--语言", args.语言, "--输出目录", output_dir],
    )
    record_result("yt-dlp 字幕/音频获取", result, report_lines)
    if transcript_ready(output_dir):
        return

    media_files = sorted(
        (path for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() in DOWNLOADED_MEDIA_SUFFIXES),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not media_files:
        detail = compact_error(result)
        raise WorkflowError("获取字幕或媒体", detail or "没有获得字幕、音频或视频。")

    media_path = media_files[0]
    report_lines.append(f"- 找到本地媒体，进入 faster-whisper 转写：{media_path.name}")
    run_required(
        "转写下载的媒体",
        "转写音频.py",
        [media_path, "--模型", args.转写模型, "--输出目录", output_dir],
        report_lines,
    )


def run_required(stage: str, script: str, args: list[object], report_lines: list[str]) -> None:
    result = run_script(script, args)
    record_result(stage, result, report_lines)
    if result.returncode != 0:
        raise WorkflowError(stage, compact_error(result) or f"{script} 退出码 {result.returncode}")


def run_script(script: str, args: list[object]) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT_DIR / script), *[str(value) for value in args]]
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def record_result(stage: str, result: subprocess.CompletedProcess[str], report_lines: list[str]) -> None:
    status = "通过" if result.returncode == 0 else f"失败（退出码 {result.returncode}）"
    report_lines.append(f"- {stage}：{status}")
    output = (result.stdout or "").strip()
    if output:
        print(output)
    error = (result.stderr or "").strip()
    if error:
        print(error, file=sys.stderr)


def compact_error(result: subprocess.CompletedProcess[str]) -> str:
    text = (result.stderr or result.stdout or "").strip()
    return text[-2000:] if text else ""


def transcript_ready(output_dir: Path) -> bool:
    path = output_dir / "逐字稿.md"
    return path.exists() and bool(path.read_text(encoding="utf-8-sig").strip())


def require_nonempty(path: Path, stage: str) -> None:
    if not path.exists() or not path.read_text(encoding="utf-8-sig").strip():
        raise WorkflowError(stage, f"没有生成有效文件：{path}")


def source_label(route: SourceRoute, source: str) -> str:
    if route.is_url or route.path:
        return source
    return "手动提供的长文本"


def write_report(output_dir: Path, lines: list[str]) -> Path:
    path = output_dir / "自动流程报告.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
