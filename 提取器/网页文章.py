from __future__ import annotations

from 核心模块.数据结构 import TranscriptDocument
from 核心模块.标准化 import raw_text_from_segments, split_plain_text_to_segments
from 核心模块.文本清洗 import clean_pasted_text
from 核心模块.适配器 import ExtractionNotAvailableError


MIN_ARTICLE_CHARS = 120
SHORT_ARTICLE_WARNING_CHARS = 300
NAVIGATION_HINTS = (
    "登录",
    "注册",
    "首页",
    "菜单",
    "导航",
    "广告",
    "相关推荐",
    "相关文章",
    "发表评论",
    "评论",
    "分享",
    "关注我们",
    "上一篇",
    "下一篇",
)


class WebArticleExtractor:
    def extract(self, url: str) -> TranscriptDocument:
        try:
            import trafilatura
        except ImportError as exc:
            raise ExtractionNotAvailableError("未安装 trafilatura。请先运行：python -m pip install -r 依赖清单.txt") from exc

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise ExtractionNotAvailableError("trafilatura 未能下载网页内容。")

        text = trafilatura.extract(downloaded, include_comments=False, include_tables=True) or ""
        text = clean_pasted_text(text)
        if not text:
            raise ExtractionNotAvailableError("trafilatura 未能提取到有效正文。")
        if len(text) < MIN_ARTICLE_CHARS:
            raise ExtractionNotAvailableError("提取到的正文过短，无法可靠进入知识脱水。请改用手动文本录入或复制网页正文到资料文件。")

        metadata = trafilatura.extract_metadata(downloaded)
        title = getattr(metadata, "title", "") if metadata else ""
        author = getattr(metadata, "author", "") if metadata else ""
        published_date = first_non_empty(
            getattr(metadata, "date", "") if metadata else "",
            getattr(metadata, "pubdate", "") if metadata else "",
            getattr(metadata, "published", "") if metadata else "",
        )
        segments = split_plain_text_to_segments(text)
        warnings = ["无精确时间戳：网页正文没有时间戳，已按段落输出。"]
        warnings.extend(build_quality_warnings(text, segments))
        document = TranscriptDocument(
            source_url=url,
            platform="网页文章",
            title=title or "网页文章正文",
            author=author or "",
            has_timestamps=False,
            segments=segments,
            raw_text=raw_text_from_segments(segments) or text,
            extraction_method="trafilatura",
            warnings=warnings,
        )
        document.published_date = published_date
        document.assert_has_content()
        return document


def first_non_empty(*values: object) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def build_quality_warnings(text: str, segments: list) -> list[str]:
    warnings: list[str] = []
    if len(text) < SHORT_ARTICLE_WARNING_CHARS:
        warnings.append("正文较短，请人工确认网页正文是否提取完整。")
    hint_count = sum(1 for hint in NAVIGATION_HINTS if hint in text)
    if hint_count >= 4:
        warnings.append("提取结果可能混入导航栏、评论区、推荐文章或广告，请人工检查。")
    short_segments = [segment for segment in segments if len(segment.text.strip()) <= 12]
    if segments and len(short_segments) / len(segments) > 0.6:
        warnings.append("提取结果短段落比例较高，可能不是完整正文，请人工检查。")
    return warnings
