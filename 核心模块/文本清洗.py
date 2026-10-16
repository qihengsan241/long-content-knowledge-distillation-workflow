from __future__ import annotations

import re


ZERO_WIDTH_CHARS = "\u200b\u200c\u200d\ufeff"


def clean_pasted_text(text: str) -> str:
    """清洗手动粘贴的字幕、逐字稿或正文，尽量不改写原意。"""
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u00a0", " ")
    normalized = normalized.translate({ord(char): None for char in ZERO_WIDTH_CHARS})
    lines = []
    for line in normalized.split("\n"):
        line = re.sub(r"[\t ]+", " ", line).strip()
        lines.append(line)
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def split_paragraphs(text: str) -> list[str]:
    cleaned = clean_pasted_text(text)
    if not cleaned:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()]
    if len(paragraphs) == 1:
        paragraphs = [line.strip() for line in cleaned.split("\n") if line.strip()]
    return paragraphs

