from __future__ import annotations

import os
from pathlib import Path


PRIVATE_ENV_WINDOWS = Path("C:/AI/Private/AgentState/Codex/长内容知识脱水工作流/.env")


def resolve_env_path(project_root: Path) -> Path:
    configured = os.getenv("KNOWLEDGE_DISTILLATION_ENV_FILE", "").strip()
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt" and Path("C:/AI").exists():
        return PRIVATE_ENV_WINDOWS
    return project_root / ".env"
