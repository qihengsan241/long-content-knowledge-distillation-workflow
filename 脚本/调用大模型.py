from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = PROJECT_ROOT / ".env"
DEFAULT_PROMPT = PROJECT_ROOT / "输出" / "最终提示词.md"
DEFAULT_OUTPUT = PROJECT_ROOT / "输出" / "知识脱水结果.md"
DEFAULT_LOG = PROJECT_ROOT / "输出" / "模型调用日志.md"

SUPPORTED_PROVIDERS = {"openai", "deepseek", "custom"}
DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
}


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    api_key: str
    base_url: str
    model_name: str
    temperature: float | None
    max_output_tokens: int | None


@dataclass(frozen=True)
class LogSnapshot:
    provider: str
    base_url: str
    model_name: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="读取最终提示词，调用 OpenAI-compatible API 执行知识脱水，并保存结果。")
    parser.add_argument("--env", default=str(DEFAULT_ENV), help="配置文件路径，默认：.env。")
    parser.add_argument("--输入", default=str(DEFAULT_PROMPT), help="最终提示词路径，默认：输出/最终提示词.md。")
    parser.add_argument("--输出", default=str(DEFAULT_OUTPUT), help="知识脱水结果输出路径，默认：输出/知识脱水结果.md。")
    parser.add_argument("--日志", default=str(DEFAULT_LOG), help="模型调用日志路径，默认：输出/模型调用日志.md。")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env_path = Path(args.env)
    log_path = Path(args.日志)
    prompt_path = Path(args.输入)
    output_path = Path(args.输出)
    config: ModelConfig | None = None

    try:
        config = load_model_config(env_path)
        prompt = read_final_prompt(prompt_path)
        result = call_compatible_model(prompt, config)
        if not result.strip():
            raise RuntimeError("模型返回内容为空。")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.strip() + "\n", encoding="utf-8")
        write_log(
            log_path,
            status="成功",
            snapshot=LogSnapshot(config.provider, config.base_url, config.model_name),
            prompt_path=prompt_path,
            output_path=output_path,
            prompt_chars=len(prompt),
            result_chars=len(result),
        )
        print(f"已生成知识脱水结果：{output_path}")
        print(f"已保存模型调用日志：{log_path}")
        return 0
    except Exception as exc:
        snapshot = LogSnapshot(config.provider, config.base_url, config.model_name) if config else read_log_snapshot(env_path)
        write_log(
            log_path,
            status="失败",
            snapshot=snapshot,
            prompt_path=prompt_path,
            output_path=output_path,
            prompt_chars=None,
            result_chars=None,
            error=exc,
        )
        print(f"调用大模型失败：{exc}", file=sys.stderr)
        print(f"错误信息已保存到：{log_path}", file=sys.stderr)
        print(
            "可以退回手动流程：打开 输出/最终提示词.md，复制给 ChatGPT / Claude / DeepSeek 网页端，"
            "再运行 python 脚本/保存知识脱水结果.py 粘贴返回结果。",
            file=sys.stderr,
        )
        return 1


def load_model_config(env_path: Path) -> ModelConfig:
    if not env_path.exists():
        raise FileNotFoundError("找不到 .env。请先复制 配置示例.env 为 .env，并填写 LLM_PROVIDER 和对应供应商配置。")

    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise RuntimeError("未安装 python-dotenv。请先运行：python -m pip install -r 依赖清单.txt") from exc

    load_dotenv(env_path, override=True, encoding="utf-8-sig")
    provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if not provider:
        raise ValueError("LLM_PROVIDER 为空。请在 .env 中填写 openai、deepseek 或 custom。")
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError("LLM_PROVIDER 不支持。可选值：openai、deepseek、custom。")

    prefix = provider.upper()
    api_key_name = f"{prefix}_API_KEY"
    base_url_name = f"{prefix}_BASE_URL"
    model_name_key = f"{prefix}_MODEL"

    api_key = (os.getenv(api_key_name) or "").strip()
    base_url = (os.getenv(base_url_name) or "").strip() or DEFAULT_BASE_URLS.get(provider, "")
    model_name = (os.getenv(model_name_key) or "").strip()

    if not api_key:
        raise ValueError(f"{api_key_name} 为空。请在 .env 中填写 {api_key_name}。")
    if provider == "custom" and not base_url:
        raise ValueError("CUSTOM_BASE_URL 为空。请在 .env 中填写 CUSTOM_BASE_URL。")
    if not model_name:
        raise ValueError(f"{model_name_key} 为空。请在 .env 中填写 {model_name_key}。")

    return ModelConfig(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        temperature=parse_optional_float(os.getenv("TEMPERATURE"), "TEMPERATURE"),
        max_output_tokens=parse_optional_int(os.getenv("MAX_OUTPUT_TOKENS"), "MAX_OUTPUT_TOKENS"),
    )


def read_final_prompt(prompt_path: Path) -> str:
    if not prompt_path.exists():
        raise FileNotFoundError("找不到 输出/最终提示词.md。请先运行：python 脚本/生成最终提示词.py")
    content = prompt_path.read_text(encoding="utf-8-sig").strip()
    if not content:
        raise ValueError("输出/最终提示词.md 为空。请先重新生成最终提示词。")
    return content


def call_compatible_model(prompt: str, config: ModelConfig) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("未安装 openai。请先运行：python -m pip install -r 依赖清单.txt") from exc

    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    payload: dict[str, object] = {
        "model": config.model_name,
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }
    if config.temperature is not None:
        payload["temperature"] = config.temperature
    if config.max_output_tokens is not None:
        payload["max_tokens"] = config.max_output_tokens

    response = client.chat.completions.create(**payload)
    return extract_chat_completion_text(response)


def extract_chat_completion_text(response: object) -> str:
    choices = getattr(response, "choices", []) or []
    output_parts: list[str] = []
    for choice in choices:
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            output_parts.append(content)
        elif isinstance(content, list):
            for item in content:
                text = getattr(item, "text", None)
                if isinstance(text, str):
                    output_parts.append(text)
    return "\n".join(part.strip() for part in output_parts if part and part.strip()).strip()


def parse_optional_float(value: str | None, name: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} 必须是数字，当前值无法解析。") from exc


def parse_optional_int(value: str | None, name: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} 必须是整数，当前值无法解析。") from exc
    if parsed <= 0:
        raise ValueError(f"{name} 必须大于 0。")
    return parsed


def read_log_snapshot(env_path: Path) -> LogSnapshot:
    env_values = read_env_values(env_path) if env_path.exists() else {}
    provider = (env_values.get("LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        provider = provider or "未配置"
        return LogSnapshot(provider, "未配置", "未配置")

    prefix = provider.upper()
    base_url = (
        env_values.get(f"{prefix}_BASE_URL")
        or os.getenv(f"{prefix}_BASE_URL")
        or DEFAULT_BASE_URLS.get(provider, "")
        or "未配置"
    )
    model_name = env_values.get(f"{prefix}_MODEL") or os.getenv(f"{prefix}_MODEL") or "未配置"
    return LogSnapshot(provider, base_url, model_name)


def read_env_values(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    content = env_path.read_text(encoding="utf-8-sig")
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        values[key.strip()] = raw_value.strip().strip('"').strip("'")
    return values


def write_log(
    path: Path,
    *,
    status: str,
    snapshot: LogSnapshot,
    prompt_path: Path,
    output_path: Path,
    prompt_chars: int | None,
    result_chars: int | None,
    error: Exception | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 模型调用日志",
        "",
        f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"状态：{status}",
        f"供应商：{snapshot.provider or '未配置'}",
        f"Base URL：{snapshot.base_url or '未配置'}",
        f"模型：{snapshot.model_name or '未配置'}",
        f"输入文件：{prompt_path}",
        f"输出文件：{output_path}",
        f"最终提示词字符数：{prompt_chars if prompt_chars is not None else '未读取'}",
        f"结果字符数：{result_chars if result_chars is not None else '未生成'}",
        "API Key：未写入日志",
    ]
    if error is not None:
        lines.extend(
            [
                "",
                "## 错误信息",
                "",
                f"错误类型：{error.__class__.__name__}",
                f"错误内容：{error}",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
