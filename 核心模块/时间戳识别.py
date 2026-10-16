from __future__ import annotations

import re

from 核心模块.数据结构 import TranscriptSegment
from 核心模块.文本清洗 import clean_pasted_text, split_paragraphs
from 核心模块.标准化 import clean_caption_text, normalize_timestamp, parse_srt, parse_vtt


TIME_TOKEN = r"(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[\.,]\d{1,3})?"
TIME_RANGE_RE = re.compile(
    rf"^\s*(?:\[)?(?P<start>{TIME_TOKEN})\s*(?:-->|-|~|–|—|至)\s*(?P<end>{TIME_TOKEN})(?:\])?\s*(?P<text>.*)$"
)
SINGLE_TIME_WITH_TEXT_RE = re.compile(rf"^\s*(?:\[)?(?P<start>{TIME_TOKEN})(?:\])?\s+(?P<text>.+)$")
TIME_ONLY_RE = re.compile(rf"^\s*(?:\[)?(?P<start>{TIME_TOKEN})(?:\])?\s*$")
SRT_INDEX_RE = re.compile(r"^\d+$")


def contains_timestamp(text: str) -> bool:
    cleaned = clean_pasted_text(text)
    if not cleaned:
        return False
    return any(_looks_like_timestamp_line(line.strip()) for line in cleaned.split("\n") if line.strip())


def parse_pasted_text(text: str) -> tuple[list[TranscriptSegment], bool, list[str]]:
    cleaned = clean_pasted_text(text)
    if not cleaned:
        return [], False, ["粘贴内容为空。"]

    subtitle_segments = parse_subtitle_like_text(cleaned)
    if subtitle_segments:
        return subtitle_segments, True, []

    timestamped_segments = parse_timestamped_text(cleaned)
    if timestamped_segments:
        warnings = []
        if any(segment.end == segment.start for segment in timestamped_segments):
            warnings.append("部分粘贴内容只有开始时间，结束时间已按下一条开始时间推断；最后一条结束时间与开始时间相同。")
        return timestamped_segments, True, warnings

    segments = [TranscriptSegment(text=paragraph) for paragraph in split_paragraphs(cleaned)]
    return segments, False, ["无精确时间戳：粘贴内容没有识别到时间戳，已按段落输出。"]


def parse_subtitle_like_text(text: str) -> list[TranscriptSegment]:
    cleaned = clean_pasted_text(text)
    if not cleaned or "-->" not in cleaned:
        return []
    if cleaned.lstrip().upper().startswith("WEBVTT"):
        return parse_vtt(cleaned)
    return parse_srt(cleaned) or parse_vtt("WEBVTT\n\n" + cleaned)


def parse_timestamped_text(text: str) -> list[TranscriptSegment]:
    lines = clean_pasted_text(text).split("\n")
    segments: list[TranscriptSegment] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line or line.upper() == "WEBVTT":
            index += 1
            continue
        if SRT_INDEX_RE.match(line) and index + 1 < len(lines) and TIME_RANGE_RE.match(lines[index + 1].strip()):
            index += 1
            continue

        range_match = TIME_RANGE_RE.match(line)
        if range_match:
            text_after_time = clean_caption_text(range_match.group("text"))
            index += 1
            collected = []
            while not text_after_time and index < len(lines):
                next_line = lines[index].strip()
                if not next_line:
                    index += 1
                    if collected:
                        break
                    continue
                if _looks_like_timestamp_line(next_line):
                    break
                collected.append(next_line)
                index += 1
            text_value = text_after_time or clean_caption_text(" ".join(collected))
            if text_value:
                segments.append(
                    TranscriptSegment(
                        start=normalize_timestamp(range_match.group("start")),
                        end=normalize_timestamp(range_match.group("end")),
                        text=text_value,
                    )
                )
            continue

        single_match = SINGLE_TIME_WITH_TEXT_RE.match(line)
        if single_match:
            text_value = clean_caption_text(single_match.group("text"))
            if text_value:
                start = normalize_timestamp(single_match.group("start"))
                segments.append(TranscriptSegment(start=start, end="", text=text_value))
            index += 1
            continue

        time_only_match = TIME_ONLY_RE.match(line)
        if time_only_match:
            start = normalize_timestamp(time_only_match.group("start"))
            index += 1
            collected = []
            while index < len(lines):
                next_line = lines[index].strip()
                if not next_line:
                    index += 1
                    if collected:
                        break
                    continue
                if _looks_like_timestamp_line(next_line):
                    break
                collected.append(next_line)
                index += 1
            text_value = clean_caption_text(" ".join(collected))
            if text_value:
                segments.append(TranscriptSegment(start=start, end="", text=text_value))
            continue

        index += 1

    return _infer_missing_end_times(segments)


def _looks_like_timestamp_line(line: str) -> bool:
    return bool(TIME_RANGE_RE.match(line) or SINGLE_TIME_WITH_TEXT_RE.match(line) or TIME_ONLY_RE.match(line))


def _infer_missing_end_times(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    for index, segment in enumerate(segments):
        if segment.end:
            continue
        if index + 1 < len(segments) and segments[index + 1].start:
            segment.end = segments[index + 1].start
        else:
            segment.end = segment.start
    return segments
