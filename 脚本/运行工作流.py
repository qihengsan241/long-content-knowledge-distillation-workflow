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

from 生成最终提示词 import DEFAULT_OUTPUT, DEFAULT_PROMPT, build_final_prompt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行长内容知识脱水工作流的第一阶段：拼接 Prompt 与逐字稿。")
    parser.add_argument("--输入", required=True, help="标准逐字稿 Markdown 或 JSON 文件。")
    parser.add_argument("--提示词", default=str(DEFAULT_PROMPT), help="知识脱水 Prompt 文件。")
    parser.add_argument("--黑曜石规则", default="", help="可选：黑曜石输出规则文件。")
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
        print(f"工作流完成。已生成：{output_path}")
        print("下一步：把 最终提示词.md 复制给 ChatGPT / Claude / Codex 使用。")
        return 0
    except Exception as exc:
        print(f"工作流失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

