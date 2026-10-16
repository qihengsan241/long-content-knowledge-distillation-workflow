from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STANDARD_KEYS = [
    "来源链接",
    "平台",
    "标题",
    "作者",
    "时长",
    "语言",
    "是否有时间戳",
    "逐字稿",
    "原始文本",
    "提取方式",
    "警告信息",
]


@dataclass
class TranscriptSegment:
    start: str = ""
    end: str = ""
    text: str = ""

    def to_standard_dict(self) -> dict[str, str]:
        return {
            "开始时间": self.start or "",
            "结束时间": self.end or "",
            "文本": self.text.strip(),
        }

    @classmethod
    def from_any(cls, item: Any) -> "TranscriptSegment":
        if isinstance(item, cls):
            return item
        if not isinstance(item, dict):
            return cls(text=str(item).strip())
        return cls(
            start=str(item.get("开始时间") or item.get("start") or "").strip(),
            end=str(item.get("结束时间") or item.get("end") or "").strip(),
            text=str(item.get("文本") or item.get("text") or "").strip(),
        )


@dataclass
class TranscriptDocument:
    source_url: str = ""
    platform: str = ""
    title: str = ""
    author: str = ""
    duration: str = ""
    language: str = ""
    has_timestamps: bool = False
    segments: list[TranscriptSegment] = field(default_factory=list)
    raw_text: str = ""
    extraction_method: str = ""
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.segments = [TranscriptSegment.from_any(segment) for segment in self.segments]
        if self.has_timestamps is False:
            self.has_timestamps = any(segment.start or segment.end for segment in self.segments)
        if not self.raw_text:
            self.raw_text = "\n".join(segment.text for segment in self.segments if segment.text)

    def assert_has_content(self) -> None:
        has_segment_text = any(segment.text.strip() for segment in self.segments)
        if not has_segment_text and not self.raw_text.strip():
            raise ValueError("没有提取到逐字稿或正文，不能进入知识脱水流程。")

    def to_standard_dict(self) -> dict[str, Any]:
        return {
            "来源链接": self.source_url,
            "平台": self.platform,
            "标题": self.title,
            "作者": self.author,
            "时长": self.duration,
            "语言": self.language,
            "是否有时间戳": bool(self.has_timestamps),
            "逐字稿": [segment.to_standard_dict() for segment in self.segments],
            "原始文本": self.raw_text,
            "提取方式": self.extraction_method,
            "警告信息": self.warnings,
        }

    @classmethod
    def from_standard_dict(cls, data: dict[str, Any]) -> "TranscriptDocument":
        if not isinstance(data, dict):
            raise TypeError("标准逐字稿 JSON 的顶层必须是对象。")
        return cls(
            source_url=str(data.get("来源链接") or data.get("source_url") or ""),
            platform=str(data.get("平台") or data.get("platform") or ""),
            title=str(data.get("标题") or data.get("title") or ""),
            author=str(data.get("作者") or data.get("author") or ""),
            duration=str(data.get("时长") or data.get("duration") or ""),
            language=str(data.get("语言") or data.get("language") or ""),
            has_timestamps=bool(data.get("是否有时间戳") or data.get("has_timestamps") or False),
            segments=[TranscriptSegment.from_any(item) for item in data.get("逐字稿", [])],
            raw_text=str(data.get("原始文本") or data.get("raw_text") or ""),
            extraction_method=str(data.get("提取方式") or data.get("extraction_method") or ""),
            warnings=list(data.get("警告信息") or data.get("warnings") or []),
        )

    @classmethod
    def empty(cls, *, source_url: str = "", platform: str = "", warning: str = "") -> "TranscriptDocument":
        warnings = [warning] if warning else []
        return cls(source_url=source_url, platform=platform, warnings=warnings)

