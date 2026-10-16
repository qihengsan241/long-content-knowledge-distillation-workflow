from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from 核心模块.导出器 import render_markdown
from 核心模块.数据结构 import TranscriptDocument


DEFAULT_PROMPT = PROJECT_ROOT / "资源" / "提示词" / "知识脱水提示词.md"
DEFAULT_TRANSCRIPT = PROJECT_ROOT / "输出" / "逐字稿.md"
DEFAULT_OUTPUT = PROJECT_ROOT / "输出" / "最终提示词.md"


def read_transcript(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"找不到逐字稿文件：{path}")
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        document = TranscriptDocument.from_standard_dict(data)
        document.assert_has_content()
        return render_markdown(document)
    content = path.read_text(encoding="utf-8-sig").strip()
    if not content:
        raise ValueError("逐字稿文件为空，不能生成最终提示词。")
    return content


def read_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"找不到知识脱水 Prompt 文件：{path}")
    content = path.read_text(encoding="utf-8-sig").strip()
    if not content:
        raise ValueError("知识脱水 Prompt 文件为空。请先把你的固定 Prompt 写入资源文件。")
    return content


def build_final_prompt(transcript_path: Path, prompt_path: Path, output_path: Path, obsidian_rules_path: Path | None = None) -> Path:
    prompt = read_prompt(prompt_path)
    transcript = read_transcript(transcript_path)
    parts = [
        "【以下是知识脱水规则】",
        "",
        prompt,
        "",
        "---",
        "",
        "【以下是待处理文本】",
        "",
        transcript,
        "",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="把知识脱水 Prompt 与逐字稿拼接成最终提示词文件。")
    parser.add_argument("--输入", default=str(DEFAULT_TRANSCRIPT), help="标准逐字稿 Markdown 或 JSON 文件，默认：输出/逐字稿.md。")
    parser.add_argument("--提示词", default=str(DEFAULT_PROMPT), help="知识脱水 Prompt 文件。")
    parser.add_argument("--黑曜石规则", default="", help="兼容旧参数；当前最终提示词格式不会插入该文件。")
    parser.add_argument("--输出", default=str(DEFAULT_OUTPUT), help="最终提示词输出路径。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output_path = build_final_prompt(
            transcript_path=Path(args.输入),
            prompt_path=Path(args.提示词),
            output_path=Path(args.输出),
            obsidian_rules_path=Path(args.黑曜石规则) if args.黑曜石规则 else None,
        )
        print(f"已生成最终提示词：{output_path}")
        return 0
    except Exception as exc:
        print(f"生成失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
