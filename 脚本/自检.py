from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_PROVIDERS = {"openai", "deepseek", "custom"}
DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
}


def main() -> int:
    checks = [
        check_file("知识脱水 Prompt", PROJECT_ROOT / "资源" / "提示词" / "知识脱水提示词.md"),
        check_file("逐字稿 Markdown", PROJECT_ROOT / "输出" / "逐字稿.md"),
        check_file("最终提示词", PROJECT_ROOT / "输出" / "最终提示词.md"),
        check_file(".env 配置", PROJECT_ROOT / ".env"),
        *check_llm_provider_config(),
        check_import("openai"),
        check_import("dotenv"),
        check_import("trafilatura"),
        check_import("youtube_transcript_api"),
        check_import("yt_dlp"),
        check_import("faster_whisper"),
        check_log_writable(PROJECT_ROOT / "输出" / "模型调用日志.md"),
    ]
    print("")
    print("自检结果：")
    for passed, message in checks:
        marker = "OK" if passed else "NO"
        print(f"[{marker}] {message}")
    return 0 if all(passed for passed, _ in checks) else 1


def check_file(label: str, path: Path) -> tuple[bool, str]:
    return path.exists(), f"{label}：{path}"


def check_llm_provider_config() -> list[tuple[bool, str]]:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return [
            (False, "LLM_PROVIDER：未检查，.env 不存在"),
            (False, "供应商配置：未检查，.env 不存在"),
        ]

    provider = get_env_value(env_path, "LLM_PROVIDER").lower()
    checks: list[tuple[bool, str]] = [
        (bool(provider), f"LLM_PROVIDER：{provider or '未配置'}"),
    ]
    if not provider:
        return checks + [(False, "供应商配置：未检查，LLM_PROVIDER 为空")]
    if provider not in SUPPORTED_PROVIDERS:
        return checks + [(False, "供应商配置：LLM_PROVIDER 不支持，可选 openai/deepseek/custom")]

    prefix = provider.upper()
    api_key_name = f"{prefix}_API_KEY"
    base_url_name = f"{prefix}_BASE_URL"
    model_name = f"{prefix}_MODEL"
    api_key = get_env_value(env_path, api_key_name)
    base_url = get_env_value(env_path, base_url_name) or DEFAULT_BASE_URLS.get(provider, "")
    model = get_env_value(env_path, model_name)

    checks.extend(
        [
            (bool(api_key), f"{api_key_name}：{'已配置' if api_key else '未配置或为空'}"),
            (bool(base_url), f"{base_url_name}：{base_url or '未配置或为空'}"),
            (bool(model), f"{model_name}：{model or '未配置或为空'}"),
        ]
    )
    return checks


def get_env_value(env_path: Path, key_name: str) -> str:
    value = read_env_value(env_path, key_name)
    if not value:
        value = (os.getenv(key_name) or "").strip()
    return value


def read_env_value(env_path: Path, key_name: str) -> str:
    content = env_path.read_text(encoding="utf-8-sig")
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        if key.strip() == key_name:
            return raw_value.strip().strip('"').strip("'")
    return ""


def check_import(module_name: str) -> tuple[bool, str]:
    return importlib.util.find_spec(module_name) is not None, f"Python 依赖可导入：{module_name}"


def check_log_writable(path: Path) -> tuple[bool, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    probe_path = path.with_name(path.stem + ".自检.tmp")
    try:
        probe_path.write_text("自检：可以创建模型调用日志。\n", encoding="utf-8")
        probe_path.unlink()
        return True, f"模型调用日志可创建：{path}"
    except OSError as exc:
        return False, f"模型调用日志不可创建：{path}；原因：{exc}"


if __name__ == "__main__":
    raise SystemExit(main())
