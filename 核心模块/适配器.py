from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from 核心模块.数据结构 import TranscriptDocument


class ExtractionNotAvailableError(RuntimeError):
    """当前提取器不可用，或还没有接入对应第三方工具。"""


class Extractor(Protocol):
    def extract(self, source: str) -> TranscriptDocument:
        ...


@dataclass
class CommandAdapterConfig:
    name: str
    command: list[str]
    output_format: str = "standard-json"
    cwd: str | None = None


class CommandLineJsonAdapter:
    """把第三方命令行工具接入为标准逐字稿提取器。

    command 中可使用 {input} 和 {output} 占位符。第三方工具需要把结果写到
    {output} 指向的 JSON 文件中；该 JSON 可以是标准逐字稿结构，也可以在未来
    通过子类覆盖 normalize_output 来适配。
    """

    def __init__(self, config: CommandAdapterConfig):
        self.config = config

    def extract(self, source: str) -> TranscriptDocument:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "third_party_transcript.json"
            command = [
                item.format(input=source, output=str(output_path))
                for item in self.config.command
            ]
            completed = subprocess.run(command, cwd=self.config.cwd, capture_output=True, text=True, check=False)
            if completed.returncode != 0:
                raise ExtractionNotAvailableError(
                    f"第三方工具 {self.config.name} 执行失败：{completed.stderr.strip() or completed.stdout.strip()}"
                )
            if not output_path.exists():
                raise ExtractionNotAvailableError(f"第三方工具 {self.config.name} 没有生成输出文件：{output_path}")
            return self.normalize_output(output_path, source)

    def normalize_output(self, output_path: Path, source: str) -> TranscriptDocument:
        data = json.loads(output_path.read_text(encoding="utf-8"))
        document = TranscriptDocument.from_standard_dict(data)
        if not document.source_url:
            document.source_url = source
        if not document.extraction_method:
            document.extraction_method = f"third-party:{self.config.name}"
        document.assert_has_content()
        return document

