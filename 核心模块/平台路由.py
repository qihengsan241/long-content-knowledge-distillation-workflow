from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


YOUTUBE_DOMAINS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "youtube-nocookie.com"}
BILIBILI_DOMAINS = {"bilibili.com", "www.bilibili.com", "m.bilibili.com", "b23.tv"}
DOUYIN_DOMAINS = {"douyin.com", "www.douyin.com", "v.douyin.com", "iesdouyin.com"}
XIAOHONGSHU_DOMAINS = {"xiaohongshu.com", "www.xiaohongshu.com", "xhslink.com"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg", ".opus"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt"}
TRANSCRIPT_EXTENSIONS = {".txt", ".md", ".json"}


@dataclass(frozen=True)
class SourceRoute:
    input_value: str
    platform: str
    kind: str
    is_url: bool
    path: Path | None = None
    reason: str = ""


def _hostname_matches(hostname: str, domains: set[str]) -> bool:
    return any(hostname == domain or hostname.endswith("." + domain) for domain in domains)


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def route_input(value: str) -> SourceRoute:
    value = str(value).strip()
    if not value:
        raise ValueError("输入不能为空。")

    path = Path(value).expanduser()
    if path.exists():
        suffix = path.suffix.lower()
        if suffix in SUBTITLE_EXTENSIONS:
            return SourceRoute(value, "本地字幕文件", "local_subtitle", False, path, "识别为本地字幕文件")
        if suffix in TRANSCRIPT_EXTENSIONS:
            return SourceRoute(value, "本地转录稿", "local_transcript", False, path, "识别为本地转录稿")
        return SourceRoute(value, "本地长文本", "local_text", False, path, "识别为本地长文本文件")

    if is_url(value):
        parsed = urlparse(value)
        hostname = (parsed.hostname or "").lower()
        suffix = Path(parsed.path).suffix.lower()
        if _hostname_matches(hostname, YOUTUBE_DOMAINS):
            return SourceRoute(value, "YouTube", "youtube", True, None, "识别为 YouTube 链接")
        if _hostname_matches(hostname, BILIBILI_DOMAINS):
            return SourceRoute(value, "B站", "bilibili", True, None, "识别为 B站链接")
        if _hostname_matches(hostname, DOUYIN_DOMAINS):
            return SourceRoute(value, "抖音", "douyin", True, None, "识别为抖音链接")
        if _hostname_matches(hostname, XIAOHONGSHU_DOMAINS):
            return SourceRoute(value, "小红书", "xiaohongshu", True, None, "识别为小红书链接")
        if suffix in AUDIO_EXTENSIONS:
            return SourceRoute(value, "播客音频", "audio", True, None, "识别为音频链接")
        return SourceRoute(value, "网页文章", "article", True, None, "识别为普通网页文章链接")

    return SourceRoute(value, "长篇文章文本", "raw_text", False, None, "未识别为 URL 或文件，按长文本处理")

