from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from 核心模块.数据结构 import TranscriptDocument
from 核心模块.标准化 import raw_text_from_segments, seconds_to_timestamp, segments_from_timed_items
from 核心模块.适配器 import ExtractionNotAvailableError


DEFAULT_LANGUAGES = ["zh-Hans", "zh-CN", "zh", "zh-TW", "en"]


class YouTubeTranscriptExtractor:
    def __init__(self, language_preferences: list[str] | None = None):
        self.language_preferences = language_preferences or DEFAULT_LANGUAGES

    def extract(self, url: str) -> TranscriptDocument:
        video_id = extract_video_id(url)
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError as exc:
            raise ExtractionNotAvailableError("未安装 youtube-transcript-api。请先运行：python -m pip install -r 依赖清单.txt") from exc

        try:
            transcript, transcript_kind = self._select_transcript(YouTubeTranscriptApi, video_id)
            fetched = transcript.fetch()
        except Exception as exc:
            raise ExtractionNotAvailableError(f"YouTube 字幕提取失败：{exc}") from exc

        items = to_raw_transcript_items(fetched)
        segments = segments_from_timed_items(items)
        if not segments:
            raise ExtractionNotAvailableError("youtube-transcript-api 没有返回有效字幕文本。")

        language = getattr(transcript, "language_code", "") or getattr(fetched, "language_code", "") or ""
        document = TranscriptDocument(
            source_url=url,
            platform="YouTube",
            title=f"YouTube 字幕 {video_id}",
            duration=seconds_to_timestamp(getattr(fetched, "video_duration", None)),
            language=language,
            has_timestamps=True,
            segments=segments,
            raw_text=raw_text_from_segments(segments),
            extraction_method=f"youtube-transcript-api:{transcript_kind}",
        )
        document.assert_has_content()
        return document

    def _select_transcript(self, api_class, video_id: str):
        api_instance = api_class()
        if hasattr(api_instance, "list"):
            transcript_list = api_instance.list(video_id)
        else:
            transcript_list = api_class.list_transcripts(video_id)

        try:
            return transcript_list.find_manually_created_transcript(self.language_preferences), "manual"
        except Exception:
            pass
        try:
            return transcript_list.find_generated_transcript(self.language_preferences), "generated"
        except Exception:
            pass

        manual_fallback = None
        generated_fallback = None
        for transcript in transcript_list:
            if is_transcript_generated(transcript):
                generated_fallback = generated_fallback or transcript
            else:
                manual_fallback = manual_fallback or transcript
        if manual_fallback is not None:
            return manual_fallback, "manual"
        if generated_fallback is not None:
            return generated_fallback, "generated"
        raise ExtractionNotAvailableError("没有找到可用的 YouTube 字幕。")


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname.endswith("youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]
    elif "youtube.com" in hostname:
        query_id = parse_qs(parsed.query).get("v", [""])[0]
        parts = [part for part in parsed.path.split("/") if part]
        if query_id:
            video_id = query_id
        elif parts and parts[0] in {"shorts", "embed", "live"} and len(parts) > 1:
            video_id = parts[1]
        else:
            video_id = ""
    else:
        video_id = url.strip()
    if not video_id:
        raise ExtractionNotAvailableError("无法从输入中解析 YouTube video id。")
    return video_id


def is_transcript_generated(transcript: object) -> bool:
    value = getattr(transcript, "is_generated", None)
    if value is None:
        value = getattr(transcript, "is_generated_transcript", None)
    return bool(value)


def to_raw_transcript_items(fetched: object) -> list[object]:
    if hasattr(fetched, "to_raw_data"):
        return list(fetched.to_raw_data())
    return list(fetched)

