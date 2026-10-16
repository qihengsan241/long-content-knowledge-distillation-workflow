from __future__ import annotations

from 核心模块.适配器 import ExtractionNotAvailableError


class DouyinExtractor:
    def extract(self, source: str):
        raise ExtractionNotAvailableError(
            "抖音提取器当前是占位接口。请先接入第三方字幕/转录工具；在拿到逐字稿前不能进入知识脱水。"
        )

