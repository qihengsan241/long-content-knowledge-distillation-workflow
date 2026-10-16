from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> int:
    while True:
        print("")
        print("后半段工作流")
        print("1. 手动粘贴文本")
        print("2. 导入本地文本文件")
        print("3. 提取网页文章正文")
        print("4. 生成最终提示词")
        print("5. 调用大模型执行知识脱水")
        print("6. 手动保存知识脱水结果")
        print("7. 整理为黑曜石文件")
        print("8. 退出")
        choice = input("请选择：").strip()
        if choice == "1":
            run_script("手动文本录入.py")
        elif choice == "2":
            file_path = input("请输入本地 .txt/.md/.srt/.vtt 文件路径：").strip()
            if file_path:
                run_script("导入文本文件.py", file_path)
        elif choice == "3":
            url = input("请输入网页文章链接：").strip()
            if url:
                run_script("提取网页文章.py", url)
        elif choice == "4":
            run_script("生成最终提示词.py")
        elif choice == "5":
            run_script("调用大模型执行知识脱水.py")
        elif choice == "6":
            run_script("保存知识脱水结果.py")
        elif choice == "7":
            run_script("整理为黑曜石文件.py")
        elif choice == "8":
            print("已退出。")
            return 0
        else:
            print("无效选项，请重新选择。")


def run_script(script_name: str, *args: str) -> None:
    script_path = SCRIPT_DIR / script_name
    completed = subprocess.run([sys.executable, str(script_path), *args], check=False)
    if completed.returncode != 0:
        print(f"{script_name} 执行失败，退出码：{completed.returncode}")


if __name__ == "__main__":
    raise SystemExit(main())
