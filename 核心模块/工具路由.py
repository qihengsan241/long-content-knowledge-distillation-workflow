from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ToolRoute:
    source_url: str
    platform: str
    kind: str
    suggestions: list[str]
    resource_files: list[str]


def route_tool(source_url: str) -> ToolRoute:
    value = source_url.strip()
    hostname = _hostname(value)

    if _matches(hostname, {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "youtube-nocookie.com"}):
        return ToolRoute(
            value,
            "YouTube",
            "youtube",
            [
                "可先运行：python 脚本/提取YouTube字幕.py \"YouTube链接\"，使用 youtube-transcript-api 获取人工字幕或自动字幕。",
                "如果 youtube-transcript-api 不可用，可运行：python 脚本/下载字幕或音频.py \"YouTube链接\"，用 yt-dlp 尝试字幕；无字幕则下载音频。",
                "优先使用 YouTube 字幕读取插件复制字幕文本。",
                "也可以尝试使用 Kedou / 蝌蚪视频解析网站下载字幕。",
            ],
            ["资源/工具说明/YouTube插件使用说明.md", "资源/工具说明/Kedou使用说明.md"],
        )
    if _matches(hostname, {"bilibili.com", "www.bilibili.com", "m.bilibili.com", "b23.tv"}):
        return ToolRoute(
            value,
            "B站",
            "bilibili",
            [
                "可运行：python 脚本/下载字幕或音频.py \"B站链接\"，用 yt-dlp 尝试字幕；无字幕则下载音频。",
                "尝试使用 Kedou / 蝌蚪视频解析网站下载字幕。",
                "如果没有字幕，不要根据标题生成内容，后续可用：python 脚本/转写音频.py \"音频文件路径\"。",
            ],
            ["资源/工具说明/Kedou使用说明.md"],
        )
    if _matches(hostname, {"douyin.com", "www.douyin.com", "v.douyin.com", "iesdouyin.com"}):
        return ToolRoute(
            value,
            "抖音",
            "douyin",
            [
                "可运行：python 脚本/下载字幕或音频.py \"抖音链接\"，用 yt-dlp 尝试字幕；无字幕则下载音频。",
                "尝试使用 Kedou / 蝌蚪视频解析网站做视频解析。",
                "如果没有字幕，后续可用：python 脚本/转写音频.py \"音频文件路径\"。",
            ],
            ["资源/工具说明/Kedou使用说明.md"],
        )
    if _matches(hostname, {"xiaohongshu.com", "www.xiaohongshu.com", "xhslink.com"}):
        return ToolRoute(
            value,
            "小红书",
            "xiaohongshu",
            [
                "如果是图文，可运行：python 脚本/提取网页文章.py \"小红书链接\" 试提正文，或手动复制正文。",
                "如果是视频，可运行：python 脚本/下载字幕或音频.py \"小红书链接\"；无字幕则下载音频等待转写。",
                "不要用标题、封面、评论或弹幕脑补正文。",
            ],
            ["资源/工具说明/Kedou使用说明.md"],
        )
    if _matches(hostname, {"zhihu.com", "www.zhihu.com", "zhuanlan.zhihu.com"}):
        return _article_route(value, "知乎", "zhihu")
    if _matches(hostname, {"csdn.net", "www.csdn.net", "blog.csdn.net"}):
        return _article_route(value, "CSDN", "csdn")
    if _matches(hostname, {"cnblogs.com", "www.cnblogs.com"}):
        return _article_route(value, "博客园", "cnblogs")
    if _matches(hostname, {"jianshu.com", "www.jianshu.com"}):
        return _article_route(value, "简书", "jianshu")
    if hostname:
        return _article_route(value, "普通网页", "webpage")
    return ToolRoute(
        value,
        "其他",
        "other",
        ["未识别为常见平台。请使用可用第三方工具或手动复制逐字稿/正文。", "没有实际文本时不要进入知识脱水。"],
        [],
    )


def _article_route(source_url: str, platform: str, kind: str) -> ToolRoute:
    return ToolRoute(
        source_url,
        platform,
        kind,
        [
            f"可运行：python 脚本/提取网页文章.py \"{source_url}\"，用 trafilatura 提取正文。",
            "也可以使用 Kedou / 蝌蚪视频解析网站做文本提取，或手动复制正文后粘贴给本脚本。",
        ],
        ["资源/工具说明/Kedou使用说明.md"],
    )


def _hostname(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.hostname:
        return parsed.hostname.lower()
    return ""


def _matches(hostname: str, domains: set[str]) -> bool:
    return any(hostname == domain or hostname.endswith("." + domain) for domain in domains)
