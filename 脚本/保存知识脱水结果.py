from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "输出" / "知识脱水结果.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="保存大模型返回的知识脱水结果。")
    parser.add_argument("--输出", default=str(DEFAULT_OUTPUT), help="保存路径，默认：输出/知识脱水结果.md。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        print("请粘贴大模型生成的知识脱水结果。粘贴完成后，单独输入一行 END 结束。")
        content = read_until_end().strip()
        if not content:
            raise ValueError("没有收到有效的知识脱水结果。")
        output_path = Path(args.输出)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content + "\n", encoding="utf-8")
        print(f"已保存：{output_path}")
        return 0
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"保存知识脱水结果失败：{exc}", file=sys.stderr)
        return 1


def read_until_end() -> str:
    lines: list[str] = []
    while True:
        line = sys.stdin.readline()
        if line == "":
            break
        if line.rstrip("\n\r").strip() == "END":
            break
        lines.append(line)
    return "".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
