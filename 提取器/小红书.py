from __future__ import annotations

from 核心模块.适配器 import ExtractionNotAvailableError


class XiaohongshuExtractor:
    def extract(self, source: str):
        raise ExtractionNotAvailableError(
            "小红书提取器当前是占位接口。请先接入第三方图文/视频转录工具；在拿到正文或逐字稿前不能进入知识脱水。"
        )

