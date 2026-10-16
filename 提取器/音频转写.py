from __future__ import annotations

from pathlib import Path
import shutil

from 核心模块.数据结构 import TranscriptDocument
from 核心模块.标准化 import raw_text_from_segments, seconds_to_timestamp, segments_from_timed_items
from 核心模块.适配器 import ExtractionNotAvailableError


SUPPORTED_MEDIA_SUFFIXES = {".mp3", ".m4a", ".wav", ".webm", ".mp4"}
VIDEO_SUFFIXES = {".webm", ".mp4"}


class AudioTranscriber:
    def __init__(self, model_size: str = "small", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    def transcribe(self, audio_path: str | Path) -> TranscriptDocument:
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"找不到音频文件：{audio_path}")
        suffix = audio_path.suffix.lower()
        if suffix not in SUPPORTED_MEDIA_SUFFIXES:
            raise ExtractionNotAvailableError("只支持 mp3 / m4a / wav / webm / mp4 文件。")
        if suffix in VIDEO_SUFFIXES and shutil.which("ffmpeg") is None:
            raise ExtractionNotAvailableError("检测到视频文件，但当前 ffmpeg 不可用。请安装 ffmpeg 并加入系统 PATH。")
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ExtractionNotAvailableError("未安装 faster-whisper。请先运行：python -m pip install -r 依赖清单.txt") from exc

        model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        segments_iter, info = model.transcribe(str(audio_path), vad_filter=True)
        timed_items = [
            {"start": segment.start, "end": segment.end, "text": segment.text}
            for segment in segments_iter
        ]
        segments = segments_from_timed_items(timed_items)
        if not segments:
            raise ExtractionNotAvailableError("faster-whisper 没有转写出有效文本。")
        document = TranscriptDocument(
            source_url=str(audio_path),
            platform="本地音频/视频",
            title="本地音频/视频转写结果",
            duration=seconds_to_timestamp(getattr(info, "duration", None)),
            language=str(getattr(info, "language", "") or ""),
            has_timestamps=True,
            segments=segments,
            raw_text=raw_text_from_segments(segments),
            extraction_method="本地音频/视频转写",
        )
        document.assert_has_content()
        return document
