from __future__ import annotations

import json
import re
from pathlib import Path

from 核心模块.数据结构 import TranscriptDocument


def safe_filename(value: str, fallback: str = "逐字稿") -> str:
    value = (value or fallback).strip()
    value = re.sub(r'[\\/:*?"<>|]+', "_", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:80] or fallback


def export_json(document: TranscriptDocument, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document.to_standard_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def render_markdown(document: TranscriptDocument) -> str:
    title = document.title or "未命名逐字稿"
    lines = [
        f"# {title}",
        "",
        f"来源链接：{document.source_url}",
        f"平台：{document.platform}",
        f"作者：{document.author}",
        f"时长：{document.duration}",
        f"语言：{document.language}",
        f"是否有时间戳：{str(document.has_timestamps).lower()}",
        f"提取方式：{document.extraction_method}",
    ]
    if document.warnings:
        lines.append(f"警告信息：{'；'.join(document.warnings)}")
    lines.extend(["", "## 逐字稿", ""])
    if document.has_timestamps:
        for segment in document.segments:
            start = segment.start or "00:00:00"
            end = segment.end or start
            lines.append(f"[{start} - {end}] {segment.text}")
    else:
        for index, segment in enumerate(document.segments, start=1):
            lines.append(f"第 {index} 段：{segment.text}")
    lines.append("")
    return "\n".join(lines)


def export_markdown(document: TranscriptDocument, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(document), encoding="utf-8")
    return path


def render_obsidian_copy(document: TranscriptDocument) -> str:
    title = document.title or "未命名逐字稿"
    frontmatter = [
        "---",
        f"title: {title}",
        f"source: {document.source_url}",
        f"platform: {document.platform}",
        f"author: {document.author}",
        f"language: {document.language}",
        f"has_timestamps: {str(document.has_timestamps).lower()}",
        f"extraction_method: {document.extraction_method}",
        "---",
        "",
    ]
    return "\n".join(frontmatter) + render_markdown(document)


def export_obsidian_copy(document: TranscriptDocument, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_obsidian_copy(document), encoding="utf-8")
    return path

