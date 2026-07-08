"""引擎检测模块 - 自动发现已安装的 AI Agent 工具"""

import os
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EngineInfo:
    name: str
    display_name: str
    vendor: str
    installed: bool
    executable: Optional[str] = None
    version: Optional[str] = None
    config_dir: Optional[str] = None
    models: list[str] = field(default_factory=list)
    error: Optional[str] = None


ENGINE_DEFINITIONS = {
    "claude": {
        "display_name": "Claude Code",
        "vendor": "Anthropic",
        "executables": ["claude"],
        "config_dir": "~/.claude",
        "models": [
            "claude-opus-4-7",
            "claude-sonnet-4-6",
            "claude-haiku-4-5",
        ],
    },
    "codex": {
        "display_name": "Codex CLI",
        "vendor": "OpenAI",
        "executables": [
            "codex",
            "/Applications/Codex.app/Contents/Resources/codex",
            "~/.codex/plugins/.plugin-appserver/codex",
        ],
        "config_dir": "~/.codex",
        "models": [
            "gpt-5-codex",
            "gpt-5.1-codex",
        ],
    },
    "hermes": {
        "display_name": "Hermes Agent",
        "vendor": "Nous Research",
        "executables": ["hermes"],
        "config_dir": "~/.hermes",
        "models": [],
    },
}


def detect_all() -> list[EngineInfo]:
    results = []
    for name, definition in ENGINE_DEFINITIONS.items():
        results.append(_detect_one(name, definition))
    return results


def detect_one(name: str) -> Optional[EngineInfo]:
    definition = ENGINE_DEFINITIONS.get(name)
    if not definition:
        return None
    return _detect_one(name, definition)


def _detect_one(name: str, definition: dict) -> EngineInfo:
    executable = None
    version = None
    error = None

    candidates = list(definition["executables"])
    if name == "codex":
        env_path = os.environ.get("CODEX_CLI_PATH")
        if env_path:
            candidates.insert(0, env_path)

    for exe in candidates:
        expanded = str(Path(exe).expanduser()) if "/" in exe else exe
        path = shutil.which(expanded) or (expanded if Path(expanded).exists() else None)
        if not path:
            continue
        version = _get_version(path)
        if version:
            executable = path
            error = None
            break
        error = f"可执行文件不可用: {path}"

    if not executable:
        error = error or "未找到可执行文件"

    config_dir = Path(definition["config_dir"]).expanduser()
    if not config_dir.exists():
        if not error:
            error = "未找到配置目录"

    # 从实际配置读取模型名
    models = _detect_models(name, config_dir, definition["models"])

    return EngineInfo(
        name=name,
        display_name=definition["display_name"],
        vendor=definition["vendor"],
        installed=executable is not None and config_dir.exists(),
        executable=executable,
        version=version,
        config_dir=str(config_dir) if config_dir.exists() else None,
        models=models,
        error=error,
    )


def _detect_models(name: str, config_dir: Path, fallback: list[str]) -> list[str]:
    """从引擎配置文件中读取实际模型名"""
    if name == "claude":
        settings_file = config_dir / "settings.json"
        if settings_file.exists():
            try:
                import json
                with open(settings_file) as f:
                    settings = json.load(f)
                env = settings.get("env", {})
                model = env.get("ANTHROPIC_MODEL", "")
                if model:
                    return [model]
                # 检查 base_url 推断
                base_url = env.get("ANTHROPIC_BASE_URL", "")
                if "deepseek" in base_url:
                    return [model or "DeepSeek-V4-Pro"]
                if "openai" in base_url:
                    return [model or "gpt-5-codex"]
            except Exception:
                pass
    return fallback


def _get_version(executable: str) -> Optional[str]:
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0][:50]
    except Exception:
        pass
    return None
