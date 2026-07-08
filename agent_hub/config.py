"""配置管理"""

import json
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path.home() / ".agent-hub"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "default_engine": "claude",
    "engines": {
        "claude": {"permission_mode": "default"},
        "codex": {},
        "hermes": {},
    },
    "server": {
        "host": "127.0.0.1",
        "port": 9527,
    },
}


def load() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            stored = json.load(f)
        merged = DEFAULT_CONFIG.copy()
        _deep_merge(merged, stored)
        return merged
    return DEFAULT_CONFIG.copy()


def save(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_engine_config(engine: str) -> dict:
    config = load()
    engines = config.get("engines", {})
    return engines.get(engine, {})


def _deep_merge(base: dict, override: dict) -> None:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
