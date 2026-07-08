"""适配器抽象基类"""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class MessageChunk:
    """统一的流式消息块"""
    def __init__(self, type: str, **kwargs):
        self.type = type
        self.data = kwargs

    def to_dict(self) -> dict:
        return {"type": self.type, **self.data}


class BaseAdapter(ABC):
    """Agent CLI 适配器基类"""

    def __init__(self, executable: str, config: dict):
        self.executable = executable
        self.config = config

    @abstractmethod
    def build_command(self, prompt: str, session_id: str, cwd: str = None) -> list[str]:
        """构建子进程命令"""
        ...

    @abstractmethod
    async def chat_stream(
        self, prompt: str, session_id: str, cwd: str = None
    ) -> AsyncIterator[MessageChunk]:
        """流式对话"""
        ...

    @abstractmethod
    def parse_usage(self, raw_data: dict) -> dict:
        """从原始数据中提取 token 用量"""
        ...
