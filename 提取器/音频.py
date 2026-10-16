from __future__ import annotations

from 核心模块.适配器 import ExtractionNotAvailableError


class AudioExtractor:
    def extract(self, source: str):
        raise ExtractionNotAvailableError(
            "播客音频提取器当前是占位接口。请先接入语音转文字工具；在拿到逐字稿前不能进入知识脱水。"
        )

