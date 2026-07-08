"""编排器基类"""

from typing import Callable, Awaitable

from ..adapters.claude import ClaudeAdapter
from ..adapters.codex import CodexAdapter
from ..adapters.hermes import HermesAdapter
from ..detector import detect_one

ADAPTER_MAP = {
    "claude": ClaudeAdapter,
    "codex": CodexAdapter,
    "hermes": HermesAdapter,
}

ENGINE_DISPLAY = {
    "claude": "Claude",
    "codex": "Codex",
    "hermes": "Hermes",
}


class BaseTeamOrchestrator:
    """多引擎编排器基类"""

    def __init__(self, engines: list[str], cwd: str, config: dict):
        self.engines = engines
        self.cwd = cwd
        self.config = config
        self.total_usage: list[dict] = []

    def _get_adapter(self, engine_name: str):
        """获取引擎适配器实例"""
        engine_info = detect_one(engine_name)
        if not engine_info or not engine_info.installed:
            return None
        engine_config = self.config.get("engines", {}).get(engine_name, {})
        engine_config = engine_config.copy()
        if self.config.get("permission_mode"):
            engine_config["permission_mode"] = self.config["permission_mode"]
        adapter_cls = ADAPTER_MAP[engine_name]
        return adapter_cls(engine_info.executable, engine_config)

    async def _run_one_engine(
        self,
        prompt: str,
        engine_name: str,
        on_event: Callable[[dict], Awaitable[None]],
        phase: str = "discussion",
        round_num: int = 0,
    ) -> dict:
        """运行单个引擎，流式输出事件，返回 usage 和 content"""
        display = ENGINE_DISPLAY.get(engine_name, engine_name)
        await on_event({
            "type": "engine_start",
            "engine": engine_name,
            "display": display,
            "phase": phase,
            "round": round_num,
        })

        adapter = self._get_adapter(engine_name)
        if not adapter:
            await on_event({
                "type": "error",
                "engine": engine_name,
                "content": f"{display} 未安装或不可用",
            })
            return {"engine": engine_name, "input_tokens": 0, "output_tokens": 0,
                    "cache_read": 0, "cache_write": 0, "model": "", "content": "",
                    "error": f"{display} 未安装或不可用"}

        accumulated: list[str] = []
        final_usage: dict = {}
        has_content = False
        error_message = ""

        try:
            async for chunk in adapter.chat_stream(prompt, "", self.cwd):
                if chunk.type == "text":
                    content = chunk.data.get("content", "")
                    accumulated.append(content)
                    has_content = True
                    await on_event({
                        "type": "text_stream",
                        "engine": engine_name,
                        "content": content,
                        "phase": phase,
                        "round": round_num,
                    })

                elif chunk.type == "tool_call":
                    await on_event({
                        "type": "tool_call",
                        "engine": engine_name,
                        "tool": chunk.data.get("tool", ""),
                        "input": chunk.data.get("input", {}),
                        "phase": phase,
                        "round": round_num,
                    })

                elif chunk.type == "done":
                    final_usage = chunk.data
                    break

                elif chunk.type == "error":
                    err = chunk.data.get("content", "")
                    error_message = err or "引擎返回错误"
                    if accumulated:
                        await on_event({
                            "type": "text_stream",
                            "engine": engine_name,
                            "content": f"\n\n*[错误: {err}]*",
                            "phase": phase,
                            "round": round_num,
                        })
                    else:
                        await on_event({
                            "type": "error",
                            "engine": engine_name,
                            "content": err,
                        })
                    break

        except Exception as e:
            error_message = str(e)
            await on_event({
                "type": "error",
                "engine": engine_name,
                "content": str(e),
            })

        full_content = "".join(accumulated)
        if not has_content:
            full_content = f"*{display} 未能生成有效回复*"

        usage_entry = {
            "engine": engine_name,
            "input_tokens": final_usage.get("input_tokens", 0),
            "output_tokens": final_usage.get("output_tokens", 0),
            "cache_read": final_usage.get("cache_read", 0),
            "cache_write": final_usage.get("cache_write", 0),
            "model": final_usage.get("model") or engine_name,
            "error": error_message,
        }
        self.total_usage.append(usage_entry)

        await on_event({
            "type": "engine_done",
            "engine": engine_name,
            "usage": usage_entry,
            "full_content": full_content,
            "phase": phase,
            "round": round_num,
        })

        usage_entry["content"] = full_content
        return usage_entry

    async def run(self, user_prompt: str, on_event: Callable[[dict], Awaitable[None]]) -> list[dict]:
        raise NotImplementedError
