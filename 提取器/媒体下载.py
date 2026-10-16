from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import urllib.request

from 核心模块.数据结构 import TranscriptDocument
from 核心模块.导出器 import safe_filename
from 核心模块.标准化 import parse_srt, parse_vtt, parse_youtube_json3, raw_text_from_segments, seconds_to_timestamp
from 核心模块.适配器 import ExtractionNotAvailableError


BLOCKED_SUBTITLE_HINTS = ("live_chat", "livechat", "danmaku", "bullet", "comment")
PREFERRED_EXTENSIONS = ("vtt", "srt", "json3")
DEFAULT_LANGUAGES = ["zh-Hans", "zh-CN", "zh", "zh-TW", "en"]


@dataclass(frozen=True)
class MediaDownloadResult:
    document: TranscriptDocument | None = None
    audio_path: Path | None = None
    subtitle_path: Path | None = None
    cookie_mode: str = ""


class MediaDownloader:
    def __init__(
        self,
        output_dir: Path,
        language_preferences: list[str] | None = None,
        cookies_from_browser: str = "",
        cookies_file: str | Path | None = None,
    ):
        self.output_dir = output_dir
        self.language_preferences = language_preferences or DEFAULT_LANGUAGES
        self.cookies_from_browser = cookies_from_browser.strip().lower()
        self.cookies_file = Path(cookies_file) if cookies_file else None
        if self.cookies_from_browser and self.cookies_file:
            raise ExtractionNotAvailableError("浏览器 Cookie 模式和 Cookie 文件模式不能同时启用。")

    def extract_subtitle_or_download_audio(self, url: str) -> MediaDownloadResult:
        try:
            from yt_dlp import YoutubeDL
        except ImportError as exc:
            raise ExtractionNotAvailableError("未安装 yt-dlp。请先运行：python -m pip install -r 依赖清单.txt") from exc

        info = self._extract_info(YoutubeDL, url, self._cookie_options())
        selection = self._select_subtitle(info.get("subtitles") or {}, "manual") or self._select_subtitle(
            info.get("automatic_captions") or {}, "auto"
        )
        if selection:
            language, track, subtitle_kind = selection
            raw_caption = self._download_caption(track["url"])
            ext = (track.get("ext") or "vtt").lower()
            subtitle_path = self._save_raw_subtitle(raw_caption, info, language, ext, subtitle_kind)
            segments = parse_caption_by_extension(raw_caption, ext)
            if not segments:
                raise ExtractionNotAvailableError("yt-dlp 找到了字幕轨道，但没有解析出有效字幕。")
            document = TranscriptDocument(
                source_url=url,
                platform=str(info.get("extractor_key") or info.get("extractor") or "视频平台"),
                title=str(info.get("title") or "视频字幕"),
                author=str(info.get("uploader") or info.get("channel") or ""),
                duration=seconds_to_timestamp(info.get("duration")),
                language=language,
                has_timestamps=True,
                segments=segments,
                raw_text=raw_text_from_segments(segments),
                extraction_method=f"yt-dlp:{subtitle_kind}:{ext}",
            )
            document.assert_has_content()
            return MediaDownloadResult(document=document, subtitle_path=subtitle_path, cookie_mode=self.cookie_mode_label())

        audio_path = self._download_audio(YoutubeDL, url)
        return MediaDownloadResult(audio_path=audio_path, cookie_mode=self.cookie_mode_label())

    @staticmethod
    def _extract_info(ydl_class, url: str, extra_options: dict | None = None) -> dict:
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        if extra_options:
            options.update(extra_options)
        with ydl_class(options) as ydl:
            return ydl.extract_info(url, download=False)

    def _select_subtitle(self, captions: dict, subtitle_kind: str):
        candidates = []
        for language, tracks in captions.items():
            if is_blocked_subtitle(language):
                continue
            for track in tracks or []:
                if not is_usable_subtitle_track(language, track):
                    continue
                candidates.append((language, track, subtitle_kind))
        if not candidates:
            return None
        for preferred in self.language_preferences:
            preferred_lower = preferred.lower()
            for language, track, kind in candidates:
                language_lower = language.lower()
                if language_lower == preferred_lower or language_lower.startswith(preferred_lower.split("-")[0]):
                    return language, track, kind
        return candidates[0]

    @staticmethod
    def _download_caption(url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")

    def _save_raw_subtitle(self, content: str, info: dict, language: str, ext: str, subtitle_kind: str) -> Path:
        subtitle_dir = self.output_dir / "字幕"
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        title = safe_filename(str(info.get("title") or "字幕"))
        path = subtitle_dir / f"{title}_{language}_{subtitle_kind}.{ext}"
        path.write_text(content, encoding="utf-8")
        return path

    def _download_audio(self, ydl_class, url: str) -> Path:
        audio_dir = self.output_dir / "音频"
        audio_dir.mkdir(parents=True, exist_ok=True)
        downloaded: list[Path] = []

        def hook(status: dict) -> None:
            if status.get("status") == "finished" and status.get("filename"):
                downloaded.append(Path(status["filename"]))

        options = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": "bestaudio/best",
            "paths": {"home": str(audio_dir)},
            "outtmpl": {"default": "%(title).80s [%(id)s].%(ext)s"},
            "progress_hooks": [hook],
        }
        options.update(self._cookie_options())
        with ydl_class(options) as ydl:
            ydl.download([url])
        if downloaded:
            return downloaded[-1]
        candidates = sorted(audio_dir.glob("*"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not candidates:
            raise ExtractionNotAvailableError("没有找到字幕，也没有成功下载音频文件。")
        return candidates[0]

    def _cookie_options(self) -> dict:
        if self.cookies_from_browser:
            if self.cookies_from_browser not in {"chrome", "edge", "firefox"}:
                raise ExtractionNotAvailableError("只支持 chrome / edge / firefox 浏览器 Cookie。")
            return {"cookiesfrombrowser": (self.cookies_from_browser,)}
        if self.cookies_file:
            if not self.cookies_file.exists():
                raise FileNotFoundError("找不到 Cookie 文件，请检查 --cookies-file 指向的路径。")
            return {"cookiefile": str(self.cookies_file)}
        return {}

    def cookie_mode_label(self) -> str:
        if self.cookies_from_browser:
            return f"浏览器 Cookie 模式：{self.cookies_from_browser}"
        if self.cookies_file:
            return "Cookie 文件模式"
        return "未启用 Cookie"


def is_blocked_subtitle(value: str) -> bool:
    lowered = value.lower()
    return any(hint in lowered for hint in BLOCKED_SUBTITLE_HINTS)


def is_usable_subtitle_track(language: str, track: dict) -> bool:
    ext = (track.get("ext") or "").lower()
    url = str(track.get("url") or "").lower()
    name = str(track.get("name") or "").lower()
    if ext not in PREFERRED_EXTENSIONS:
        return False
    combined = " ".join([language.lower(), ext, url, name])
    return not any(hint in combined for hint in BLOCKED_SUBTITLE_HINTS)


def parse_caption_by_extension(content: str, ext: str):
    ext = ext.lower()
    if ext == "json3":
        return parse_youtube_json3(content)
    if ext == "srt":
        return parse_srt(content)
    return parse_vtt(content)
