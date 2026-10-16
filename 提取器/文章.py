from __future__ import annotations

import re
import urllib.request
from html.parser import HTMLParser

from 核心模块.数据结构 import TranscriptDocument
from 核心模块.标准化 import raw_text_from_segments, split_plain_text_to_segments
from 核心模块.适配器 import ExtractionNotAvailableError


class _BasicHTMLTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_ignored = False
        self.in_title = False
        self.title_parts: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.in_ignored = True
        if tag == "title":
            self.in_title = True
        if tag in {"p", "div", "section", "article", "br", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"}:
            self.in_ignored = False
        if tag == "title":
            self.in_title = False
        if tag in {"p", "div", "section", "article", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.in_ignored:
            return
        text = data.strip()
        if not text:
            return
        if self.in_title:
            self.title_parts.append(text)
        self.parts.append(text + " ")

    @property
    def text(self) -> str:
        value = "".join(self.parts)
        value = re.sub(r"\n\s*\n+", "\n\n", value)
        value = re.sub(r"[ \t]+", " ", value)
        return value.strip()

    @property
    def title(self) -> str:
        return " ".join(self.title_parts).strip()


class ArticleExtractor:
    def extract(self, source: str) -> TranscriptDocument:
        content, title, author, method, warnings = self._extract_with_trafilatura(source)
        if not content:
            content, title, method, fallback_warning = self._extract_with_basic_html(source)
            warnings.append(fallback_warning)
        if not content:
            raise ExtractionNotAvailableError("网页文章正文提取失败，没有拿到可用于知识脱水的正文。")

        segments = split_plain_text_to_segments(content)
        document = TranscriptDocument(
            source_url=source,
            platform="网页文章",
            title=title or "网页文章正文",
            author=author,
            has_timestamps=False,
            segments=segments,
            raw_text=raw_text_from_segments(segments) or content,
            extraction_method=method,
            warnings=warnings,
        )
        document.assert_has_content()
        return document

    @staticmethod
    def _extract_with_trafilatura(source: str) -> tuple[str, str, str, str, list[str]]:
        warnings: list[str] = []
        try:
            import trafilatura
        except ImportError:
            return "", "", "", "basic-html-fallback", ["未安装 trafilatura，已尝试使用基础 HTML 提取。"]

        downloaded = trafilatura.fetch_url(source)
        if not downloaded:
            return "", "", "", "trafilatura", ["trafilatura 未能下载网页，已尝试基础 HTML 提取。"]
        content = trafilatura.extract(downloaded, include_comments=False, include_tables=True) or ""
        metadata = trafilatura.extract_metadata(downloaded)
        title = getattr(metadata, "title", "") if metadata else ""
        author = getattr(metadata, "author", "") if metadata else ""
        return content.strip(), title or "", author or "", "trafilatura", warnings

    @staticmethod
    def _extract_with_basic_html(source: str) -> tuple[str, str, str, str]:
        request = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
        parser = _BasicHTMLTextParser()
        parser.feed(html)
        return parser.text, parser.title, "basic-html-fallback", "基础 HTML 提取精度有限，建议安装 trafilatura。"

