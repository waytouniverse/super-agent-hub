"""Hermes Agent 适配器（待实现）"""

from typing import AsyncIterator

from .base import BaseAdapter, MessageChunk


class HermesAdapter(BaseAdapter):
    """Hermes Agent 适配器 - Hermes 未安装，预留接口"""

    def build_command(self, prompt: str, session_id: str, cwd: str = None) -> list[str]:
        return [
            self.executable, "run",
            "--session-id", session_id,
            prompt,
        ]

    async def chat_stream(
        self, prompt: str, session_id: str, cwd: str = None
    ) -> AsyncIterator[MessageChunk]:
        yield MessageChunk(
            "error",
            content="Hermes 适配器暂未实现。请先使用 claude 引擎。",
        )

    def parse_usage(self, raw_data: dict) -> dict:
        return {
            "input_tokens": raw_data.get("input_tokens", 0),
            "output_tokens": raw_data.get("output_tokens", 0),
            "cache_read": 0,
            "cache_write": 0,
        }
