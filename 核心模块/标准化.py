from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Iterable

from 核心模块.数据结构 import TranscriptDocument, TranscriptSegment


TIMESTAMP_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?)\s*(?:-->|-|至)\s*"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?)"
)
MARKDOWN_SEGMENT_RE = re.compile(
    r"^\[(?P<start>[^\]]+?)\s*-\s*(?P<end>[^\]]+?)\]\s*(?P<text>.+)$"
)
PARAGRAPH_RE = re.compile(r"^\s*第\s*(?P<num>\d+)\s*段[:：]\s*(?P<text>.+)$")
LOOSE_TIME_TOKEN = r"(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[\.,]\d{1,3})?"
LOOSE_TIME_RANGE_RE = re.compile(
    rf"^\s*(?:\[)?(?P<start>{LOOSE_TIME_TOKEN})\s*(?:-->|-|~|–|—|至)\s*(?P<end>{LOOSE_TIME_TOKEN})(?:\])?\s*(?P<text>.*)$"
)
LOOSE_SINGLE_TIME_RE = re.compile(rf"^\s*(?:\[)?(?P<start>{LOOSE_TIME_TOKEN})(?:\])?\s+(?P<text>.+)$")


def seconds_to_timestamp(seconds: float | int | None) -> str:
    if seconds is None:
        return ""
    total_seconds = int(float(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def normalize_timestamp(value: str) -> str:
    value = value.strip().replace(",", ".")
    if not value:
        return ""
    parts = value.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        hours = "0"
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        return value
    seconds = seconds.split(".")[0]
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"


def clean_caption_text(value: str) -> str:
    value = re.sub(r"<\d{1,2}:\d{2}:\d{2}\.\d{1,3}>", "", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = value.replace("\ufeff", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def raw_text_from_segments(segments: Iterable[TranscriptSegment]) -> str:
    return "\n".join(segment.text for segment in segments if segment.text.strip())


def segments_from_timed_items(items: Iterable[object]) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    for item in items:
        if isinstance(item, dict):
            text = str(item.get("text") or item.get("文本") or "").strip()
            start_value = item.get("start", item.get("开始时间"))
            duration_value = item.get("duration")
            end_value = item.get("end", item.get("结束时间"))
        else:
            text = str(getattr(item, "text", "") or "").strip()
            start_value = getattr(item, "start", None)
            duration_value = getattr(item, "duration", None)
            end_value = getattr(item, "end", None)
        text = clean_caption_text(text)
        if not text:
            continue
        start_seconds = _to_optional_float(start_value)
        duration_seconds = _to_optional_float(duration_value)
        end_seconds = _to_optional_float(end_value)
        if end_seconds is None and start_seconds is not None and duration_seconds is not None:
            end_seconds = start_seconds + duration_seconds
        segments.append(
            TranscriptSegment(
                start=seconds_to_timestamp(start_seconds) if start_seconds is not None else str(start_value or ""),
                end=seconds_to_timestamp(end_seconds) if end_seconds is not None else "",
                text=text,
            )
        )
    return merge_duplicate_segments(_infer_missing_segment_ends(segments))


def parse_youtube_json3(content: str) -> list[TranscriptSegment]:
    data = json.loads(content)
    items = []
    for event in data.get("events", []):
        pieces = event.get("segs") or []
        text = "".join(piece.get("utf8", "") for piece in pieces)
        if not text.strip():
            continue
        start_ms = event.get("tStartMs")
        duration_ms = event.get("dDurationMs")
        item = {
            "start": float(start_ms) / 1000 if start_ms is not None else None,
            "duration": float(duration_ms) / 1000 if duration_ms is not None else None,
            "text": text,
        }
        items.append(item)
    return segments_from_timed_items(items)


def parse_vtt(content: str) -> list[TranscriptSegment]:
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    segments: list[TranscriptSegment] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("Kind:") or line.startswith("Language:"):
            index += 1
            continue
        match = TIMESTAMP_RE.search(line)
        if not match:
            index += 1
            continue
        start = normalize_timestamp(match.group("start"))
        end = normalize_timestamp(match.group("end"))
        inline_text = line[match.end() :].strip()
        index += 1
        text_lines: list[str] = []
        if inline_text:
            text_lines.append(inline_text)
        else:
            while index < len(lines) and lines[index].strip():
                text_lines.append(lines[index].strip())
                index += 1
        text = clean_caption_text(" ".join(text_lines))
        if text:
            segments.append(TranscriptSegment(start=start, end=end, text=text))
    return merge_duplicate_segments(segments)


def parse_srt(content: str) -> list[TranscriptSegment]:
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").replace("\r", "\n").strip())
    segments: list[TranscriptSegment] = []
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        timestamp_line = next((line for line in lines if "-->" in line), "")
        if not timestamp_line:
            continue
        match = TIMESTAMP_RE.search(timestamp_line)
        if not match:
            continue
        timestamp_index = lines.index(timestamp_line)
        inline_text = timestamp_line[match.end() :].strip()
        text_source = [inline_text] if inline_text else lines[timestamp_index + 1 :]
        text = clean_caption_text(" ".join(text_source))
        if text:
            segments.append(
                TranscriptSegment(
                    start=normalize_timestamp(match.group("start")),
                    end=normalize_timestamp(match.group("end")),
                    text=text,
                )
            )
    return merge_duplicate_segments(segments)


def parse_loose_timestamped_text(content: str) -> list[TranscriptSegment]:
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    segments: list[TranscriptSegment] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.upper() == "WEBVTT":
            continue
        range_match = LOOSE_TIME_RANGE_RE.match(line)
        if range_match:
            text = clean_caption_text(range_match.group("text"))
            if text:
                segments.append(
                    TranscriptSegment(
                        start=normalize_timestamp(range_match.group("start")),
                        end=normalize_timestamp(range_match.group("end")),
                        text=text,
                    )
                )
            continue
        single_match = LOOSE_SINGLE_TIME_RE.match(line)
        if single_match:
            text = clean_caption_text(single_match.group("text"))
            if text:
                segments.append(
                    TranscriptSegment(
                        start=normalize_timestamp(single_match.group("start")),
                        end="",
                        text=text,
                    )
                )
    return merge_duplicate_segments(_infer_missing_segment_ends(segments))


def _infer_missing_segment_ends(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    for index, segment in enumerate(segments):
        if segment.end:
            continue
        if index + 1 < len(segments) and segments[index + 1].start:
            segment.end = segments[index + 1].start
        else:
            segment.end = segment.start
    return segments


def _to_optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    value_text = str(value).strip()
    if not value_text:
        return None
    if ":" in value_text:
        parts = [float(part.replace(",", ".")) for part in value_text.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return float(value_text)


def merge_duplicate_segments(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    merged: list[TranscriptSegment] = []
    for segment in segments:
        if merged and merged[-1].start == segment.start and merged[-1].end == segment.end and merged[-1].text == segment.text:
            continue
        merged.append(segment)
    return merged


def parse_markdown_transcript(content: str) -> tuple[list[TranscriptSegment], bool]:
    segments: list[TranscriptSegment] = []
    in_transcript = False
    for raw_line in content.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## ") and "逐字稿" in line:
            in_transcript = True
            continue
        if line.startswith("#"):
            continue
        timestamp_match = MARKDOWN_SEGMENT_RE.match(line)
        if timestamp_match:
            segments.append(
                TranscriptSegment(
                    start=normalize_timestamp(timestamp_match.group("start")),
                    end=normalize_timestamp(timestamp_match.group("end")),
                    text=timestamp_match.group("text").strip(),
                )
            )
            continue
        paragraph_match = PARAGRAPH_RE.match(line)
        if paragraph_match:
            segments.append(TranscriptSegment(text=paragraph_match.group("text").strip()))
            continue
        if in_transcript and not line.startswith(("来源链接：", "平台：", "作者：", "时长：", "语言：", "是否有时间戳：", "提取方式：")):
            segments.append(TranscriptSegment(text=line))
    return segments, any(segment.start or segment.end for segment in segments)


def extract_markdown_metadata(content: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    key_map = {
        "来源链接": "source_url",
        "平台": "platform",
        "作者": "author",
        "时长": "duration",
        "语言": "language",
        "是否有时间戳": "has_timestamps",
        "提取方式": "extraction_method",
    }
    for raw_line in content.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if line.startswith("# ") and "title" not in metadata:
            metadata["title"] = line[2:].strip()
            continue
        for label, key in key_map.items():
            prefix = f"{label}："
            if line.startswith(prefix):
                metadata[key] = line[len(prefix) :].strip()
                break
    return metadata


def split_plain_text_to_segments(content: str) -> list[TranscriptSegment]:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    if len(paragraphs) == 1:
        paragraphs = [line.strip() for line in normalized.split("\n") if line.strip()]
    return [TranscriptSegment(text=paragraph) for paragraph in paragraphs]


def document_from_json_file(path: Path) -> TranscriptDocument:
    data = json.loads(path.read_text(encoding="utf-8"))
    document = TranscriptDocument.from_standard_dict(data)
    if not document.platform:
        document.platform = "本地转录稿"
    if not document.extraction_method:
        document.extraction_method = "local-json"
    if not document.source_url:
        document.source_url = str(path)
    document.assert_has_content()
    return document


def document_from_subtitle_file(path: Path) -> TranscriptDocument:
    content = path.read_text(encoding="utf-8-sig")
    suffix = path.suffix.lower()
    if suffix == ".vtt":
        segments = parse_vtt(content)
        method = "local-vtt"
    else:
        segments = parse_srt(content)
        method = "local-srt"
    document = TranscriptDocument(
        source_url=str(path),
        platform="本地字幕文件",
        title=path.stem,
        has_timestamps=True,
        segments=segments,
        raw_text=raw_text_from_segments(segments),
        extraction_method=method,
    )
    document.assert_has_content()
    return document


def document_from_text_file(path: Path) -> TranscriptDocument:
    if path.suffix.lower() == ".json":
        return document_from_json_file(path)
    content = path.read_text(encoding="utf-8-sig")
    metadata: dict[str, str] = {}
    if path.suffix.lower() == ".md":
        metadata = extract_markdown_metadata(content)
        segments, has_timestamps = parse_markdown_transcript(content)
        if not segments:
            segments = split_plain_text_to_segments(content)
            has_timestamps = False
    else:
        segments = parse_loose_timestamped_text(content)
        has_timestamps = bool(segments)
        if not segments:
            segments = split_plain_text_to_segments(content)
            has_timestamps = False
    document = TranscriptDocument(
        source_url=metadata.get("source_url") or str(path),
        platform=metadata.get("platform") or "本地转录稿",
        title=metadata.get("title") or path.stem,
        author=metadata.get("author") or "",
        duration=metadata.get("duration") or "",
        language=metadata.get("language") or "",
        has_timestamps=has_timestamps,
        segments=segments,
        raw_text=raw_text_from_segments(segments) or content.strip(),
        extraction_method=metadata.get("extraction_method") or f"local-{path.suffix.lower().lstrip('.') or 'text'}",
    )
    document.assert_has_content()
    return document


def document_from_raw_text(value: str) -> TranscriptDocument:
    segments = split_plain_text_to_segments(value)
    document = TranscriptDocument(
        platform="长篇文章文本",
        title="长篇文章文本",
        has_timestamps=False,
        segments=segments,
        raw_text=raw_text_from_segments(segments) or value.strip(),
        extraction_method="raw-text",
        warnings=["输入未识别为 URL 或本地文件，已按长篇文章文本处理。"],
    )
    document.assert_has_content()
    return document
