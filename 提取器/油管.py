from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any

from 核心模块.数据结构 import TranscriptDocument, TranscriptSegment
from 核心模块.标准化 import clean_caption_text, parse_srt, parse_vtt, raw_text_from_segments, seconds_to_timestamp
from 核心模块.适配器 import ExtractionNotAvailableError


@dataclass
class CaptionSelection:
    language: str
    caption_type: str
    track: dict[str, Any]


class YouTubeExtractor:
    def __init__(self, language_preferences: list[str] | None = None, allow_auto_captions: bool = True):
        self.language_preferences = language_preferences or ["zh-Hans", "zh-CN", "zh", "zh-TW", "en"]
        self.allow_auto_captions = allow_auto_captions

    def extract(self, source: str) -> TranscriptDocument:
        try:
            from yt_dlp import YoutubeDL
        except ImportError as exc:
            raise ExtractionNotAvailableError("未安装 yt-dlp。请先运行：python -m pip install yt-dlp") from exc

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": self.allow_auto_captions,
            "subtitlesformat": "vtt/json3/srt/best",
        }
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(source, download=False)

        selection = self._select_caption(info)
        if selection is None:
            raise ExtractionNotAvailableError("YouTube 没有找到可下载字幕。禁止根据标题或简介脑补内容。")

        raw_caption = self._download_caption(selection.track["url"])
        extension = (selection.track.get("ext") or "").lower()
        if extension == "json3":
            segments = self._parse_json3(raw_caption)
        elif extension == "srt":
            segments = parse_srt(raw_caption)
        else:
            segments = parse_vtt(raw_caption)

        if not segments:
            raise ExtractionNotAvailableError("字幕文件已下载，但没有解析出有效逐字稿。")

        document = TranscriptDocument(
            source_url=source,
            platform="YouTube",
            title=str(info.get("title") or "YouTube 逐字稿"),
            author=str(info.get("uploader") or info.get("channel") or ""),
            duration=seconds_to_timestamp(info.get("duration")),
            language=selection.language,
            has_timestamps=True,
            segments=segments,
            raw_text=raw_text_from_segments(segments),
            extraction_method=f"yt-dlp:{selection.caption_type}:{extension or 'vtt'}",
        )
        document.assert_has_content()
        return document

    def _select_caption(self, info: dict[str, Any]) -> CaptionSelection | None:
        subtitle_groups: list[tuple[str, dict[str, Any]]] = [("manual-subtitle", info.get("subtitles") or {})]
        if self.allow_auto_captions:
            subtitle_groups.append(("auto-caption", info.get("automatic_captions") or {}))

        for caption_type, captions in subtitle_groups:
            exact = self._find_language(captions, exact=True)
            if exact:
                language, tracks = exact
                return CaptionSelection(language, caption_type, self._choose_track(tracks))
            fuzzy = self._find_language(captions, exact=False)
            if fuzzy:
                language, tracks = fuzzy
                return CaptionSelection(language, caption_type, self._choose_track(tracks))

        for caption_type, captions in subtitle_groups:
            for language, tracks in captions.items():
                if tracks:
                    return CaptionSelection(language, caption_type, self._choose_track(tracks))
        return None

    def _find_language(self, captions: dict[str, Any], *, exact: bool) -> tuple[str, list[dict[str, Any]]] | None:
        for preferred in self.language_preferences:
            preferred_lower = preferred.lower()
            for language, tracks in captions.items():
                language_lower = language.lower()
                is_match = language_lower == preferred_lower if exact else language_lower.startswith(preferred_lower.split("-")[0])
                if is_match and tracks:
                    return language, tracks
        return None

    @staticmethod
    def _choose_track(tracks: list[dict[str, Any]]) -> dict[str, Any]:
        order = {"vtt": 0, "json3": 1, "srt": 2}
        return sorted(tracks, key=lambda item: order.get((item.get("ext") or "").lower(), 99))[0]

    @staticmethod
    def _download_caption(url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")

    @staticmethod
    def _parse_json3(content: str) -> list[TranscriptSegment]:
        data = json.loads(content)
        segments: list[TranscriptSegment] = []
        for event in data.get("events", []):
            pieces = event.get("segs") or []
            text = clean_caption_text("".join(piece.get("utf8", "") for piece in pieces))
            if not text:
                continue
            start_ms = int(event.get("tStartMs") or 0)
            duration_ms = int(event.get("dDurationMs") or 0)
            end_ms = start_ms + duration_ms if duration_ms else start_ms
            segments.append(
                TranscriptSegment(
                    start=seconds_to_timestamp(start_ms / 1000),
                    end=seconds_to_timestamp(end_ms / 1000),
                    text=text,
                )
            )
        return segments

