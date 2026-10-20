from __future__ import annotations

import os
from pathlib import Path
import shutil

from 核心模块.数据结构 import TranscriptDocument
from 核心模块.标准化 import raw_text_from_segments, seconds_to_timestamp, segments_from_timed_items
from 核心模块.适配器 import ExtractionNotAvailableError


SUPPORTED_MEDIA_SUFFIXES = {".mp3", ".m4a", ".wav", ".webm", ".mp4"}
VIDEO_SUFFIXES = {".webm", ".mp4"}


class AudioTranscriber:
    def __init__(
        self,
        model_size: str = "small",
        device: str = "auto",
        compute_type: str = "auto",
        model_cache: str | Path | None = None,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model_cache = Path(model_cache) if model_cache else self._default_model_cache()
        self.resolved_device = ""
        self.resolved_compute_type = ""

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

        device, compute_type = self.resolve_runtime()
        warnings: list[str] = []
        model_kwargs = {
            "device": device,
            "compute_type": compute_type,
        }
        if self.model_cache:
            self.model_cache.mkdir(parents=True, exist_ok=True)
            model_kwargs["download_root"] = str(self.model_cache)

        try:
            model = WhisperModel(self.model_size, **model_kwargs)
        except Exception as exc:
            if self.device == "auto" and device == "cuda" and self._is_cuda_runtime_error(exc):
                device = "cpu"
                compute_type = "int8"
                model_kwargs.update(device=device, compute_type=compute_type)
                warnings.append("CUDA 运行环境不可用，已自动回退到 CPU / int8。")
                model = WhisperModel(self.model_size, **model_kwargs)
            else:
                raise

        self.resolved_device = device
        self.resolved_compute_type = compute_type
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
            warnings=warnings + [
                f"转写运行环境：{device} / {compute_type} / 模型 {self.model_size}。"
            ],
        )
        document.assert_has_content()
        return document

    def resolve_runtime(self) -> tuple[str, str]:
        device = self.device.strip().lower() or "auto"
        compute_type = self.compute_type.strip().lower() or "auto"

        if device == "auto":
            try:
                import ctranslate2

                device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            except (ImportError, RuntimeError):
                device = "cpu"

        if compute_type == "auto":
            compute_type = "int8_float16" if device == "cuda" else "int8"
        return device, compute_type

    @staticmethod
    def _is_cuda_runtime_error(error: Exception) -> bool:
        message = str(error).lower()
        return any(
            marker in message
            for marker in ("cuda", "cudnn", "cublas", "nvidia", "out of memory")
        )

    @staticmethod
    def _default_model_cache() -> Path | None:
        configured = os.environ.get("KNOWLEDGE_DISTILLATION_MODEL_CACHE", "").strip()
        if configured:
            return Path(configured)

        shared_models = Path("D:/AI/Shared/Models")
        if os.name == "nt" and shared_models.exists():
            return shared_models / "faster-whisper"
        return None
