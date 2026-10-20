from __future__ import annotations

import argparse
from datetime import datetime
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from 核心模块.导出器 import export_json
from 核心模块.数据结构 import TranscriptDocument
from 核心模块.适配器 import ExtractionNotAvailableError
from 提取器.音频转写 import AudioTranscriber


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "输出"
SUPPORTED_SUFFIXES = {".mp3", ".m4a", ".wav", ".webm", ".mp4"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="使用 faster-whisper 转写本地音频/视频文件并导出标准逐字稿。")
    parser.add_argument("音频文件", help="本地音频或视频文件路径，支持 mp3/m4a/wav/webm/mp4。")
    parser.add_argument("--模型", default="small", help="faster-whisper 模型名，默认：small。")
    parser.add_argument("--设备", default="auto", help="运行设备，默认：auto（优先 CUDA，失败时使用 CPU）。")
    parser.add_argument("--计算类型", default="auto", help="compute_type，默认：auto。")
    parser.add_argument("--模型缓存", default="", help="可选模型缓存目录；本机默认使用 D:/AI/Shared/Models/faster-whisper。")
    parser.add_argument("--输出目录", default=str(DEFAULT_OUTPUT_DIR), help="输出目录，默认：输出/。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.音频文件)
    output_dir = Path(args.输出目录)
    try:
        validate_input_file(input_path)
        transcriber = AudioTranscriber(
            args.模型,
            args.设备,
            args.计算类型,
            args.模型缓存 or None,
        )
        document = transcriber.transcribe(args.音频文件)
        markdown_path = export_transcription_markdown(document, output_dir / "逐字稿.md")
        json_path = export_json(document, output_dir / "逐字稿.json")
        print("音频转写完成。")
        print(f"运行环境：{transcriber.resolved_device} / {transcriber.resolved_compute_type}")
        print(f"已生成：{markdown_path}")
        print(f"已生成：{json_path}")
        return 0
    except ExtractionNotAvailableError as exc:
        write_failure_report(output_dir / "音频转写失败报告.md", input_path, exc, "依赖或转写能力不可用")
        print(f"音频转写失败：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        write_failure_report(output_dir / "音频转写失败报告.md", input_path, exc, "运行异常")
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1


def validate_input_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"找不到音频/视频文件：{path}")
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ExtractionNotAvailableError("只支持 mp3 / m4a / wav / webm / mp4 文件。")


def export_transcription_markdown(document: TranscriptDocument, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 本地音频/视频转写结果",
        "",
        f"来源文件：{document.source_url}",
        "提取方式：本地音频/视频转写",
        "是否有时间戳：true",
        "",
        "## 逐字稿",
        "",
    ]
    for segment in document.segments:
        start = segment.start or "00:00:00"
        end = segment.end or start
        lines.append(f"[{start} - {end}] {segment.text}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_failure_report(path: Path, input_path: Path, error: Exception, stage: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 音频转写失败报告",
        "",
        f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"输入文件：{input_path}",
        f"失败阶段：{stage}",
        f"错误类型：{error.__class__.__name__}",
        f"错误信息：{error}",
        "",
        "## 下一步建议",
        "",
        "- 如果文件不存在，请重新选择本地音频/视频文件。",
        "- 如果是视频文件，请安装 ffmpeg 并加入系统 PATH。",
        "- 如果提示未安装 faster-whisper，请运行：python -m pip install -r 依赖清单.txt。",
        "- 如果转写结果为空，请检查音频是否有人声，或先手动转写后导入文本。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
