from __future__ import annotations

import argparse
from datetime import datetime
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "输出" / "知识脱水结果.md"
DEFAULT_OUTPUT = PROJECT_ROOT / "输出" / "黑曜石笔记.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="把知识脱水结果包装成适合保存到黑曜石的 Markdown 文件。")
    parser.add_argument("--输入", default=str(DEFAULT_INPUT), help="知识脱水结果路径，默认：输出/知识脱水结果.md。")
    parser.add_argument("--输出", default=str(DEFAULT_OUTPUT), help="黑曜石笔记输出路径，默认：输出/黑曜石笔记.md。")
    parser.add_argument("--来源", default="", help="可选：写入 YAML 的来源字段。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        input_path = Path(args.输入)
        if not input_path.exists():
            raise FileNotFoundError(f"找不到知识脱水结果文件：{input_path}")
        body = input_path.read_text(encoding="utf-8-sig").strip()
        if not body:
            raise ValueError("知识脱水结果文件为空。")
        output_path = Path(args.输出)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(build_obsidian_markdown(body, args.来源), encoding="utf-8")
        print(f"已生成：{output_path}")
        return 0
    except Exception as exc:
        print(f"整理为黑曜石文件失败：{exc}", file=sys.stderr)
        return 1


def build_obsidian_markdown(body: str, source: str = "") -> str:
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    yaml = [
        "---",
        "类型: 知识脱水结果",
        "状态: 草稿",
        f"来源: {source}",
        f"创建时间: {created_at}",
        "标签:",
        "  - 知识脱水",
        "  - 长内容处理",
        "---",
        "",
    ]
    return "\n".join(yaml) + body.strip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())

