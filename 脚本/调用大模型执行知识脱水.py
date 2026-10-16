from __future__ import annotations

import sys
from pathlib import Path


# 中文入口；实际多供应商执行逻辑在同目录的 调用大模型.py 中。
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from 调用大模型 import main


if __name__ == "__main__":
    raise SystemExit(main())
