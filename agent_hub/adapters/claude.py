"""Claude Code 适配器"""

import asyncio
import json
import os
from typing import AsyncIterator

from .base import BaseAdapter, MessageChunk


class ClaudeAdapter(BaseAdapter):
    """通过 claude -p --output-format stream-json 子进程调用"""

    def build_command(self, prompt: str, session_id: str, cwd: str = None) -> list[str]:
        cmd = [
            self.executable,
            "-p",
            "--output-format", "stream-json",
            "--verbose",
        ]
        model = self.config.get("model")
        if model:
            cmd.extend(["--model", model])
        permission = self.config.get("permission_mode", "default")
        if permission != "default":
            cmd.extend(["--permission-mode", permission])
        allowed_tools = self.config.get("allowed_tools", [])
        if allowed_tools:
            cmd.append(f"--allowedTools={','.join(allowed_tools)}")
        cmd.append(prompt)
        return cmd

    async def chat_stream(
        self, prompt: str, session_id: str, cwd: str = None
    ) -> AsyncIterator[MessageChunk]:
        cmd = self.build_command(prompt, session_id, cwd)
        env = os.environ.copy()

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )

        try:
            async for line in proc.stdout:
                line = line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type", "")

                if msg_type == "assistant":
                    message = data.get("message", {})
                    content = message.get("content", [])
                    for block in content:
                        if isinstance(block, dict):
                            block_type = block.get("type", "")
                            if block_type == "text":
                                yield MessageChunk("text", content=block.get("text", ""))
                            elif block_type == "tool_use":
                                yield MessageChunk(
                                    "tool_call",
                                    tool=block.get("name", ""),
                                    tool_id=block.get("id", ""),
                                    input=block.get("input", {}),
                                )
                            elif block_type == "tool_result":
                                yield MessageChunk(
                                    "tool_result",
                                    tool_id=block.get("tool_use_id", ""),
                                    content=block.get("content", ""),
                                )

                elif msg_type == "user":
                    message = data.get("message", {})
                    for block in message.get("content", []):
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            yield MessageChunk(
                                "tool_result",
                                tool_id=block.get("tool_use_id", ""),
                                content=block.get("content", ""),
                            )

                elif msg_type == "result":
                    usage = data.get("usage", {})
                    model_usage = data.get("modelUsage", {})
                    model = list(model_usage.keys())[0] if model_usage else self.config.get("model", "claude-sonnet-4-6")
                    yield MessageChunk(
                        "done",
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        cache_read=usage.get("cache_read_input_tokens", 0),
                        cache_write=usage.get("cache_creation_input_tokens", 0),
                        model=model,
                    )

                elif msg_type == "error":
                    yield MessageChunk("error", content=data.get("message", "未知错误"))

            return_code = await proc.wait()
            if return_code != 0:
                stderr = ""
                if proc.stderr:
                    stderr = (await proc.stderr.read()).decode("utf-8", errors="replace").strip()
                yield MessageChunk(
                    "error",
                    content=stderr or f"Claude Code 退出，状态码 {return_code}",
                )

        except asyncio.CancelledError:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
            raise
        except Exception as e:
            yield MessageChunk("error", content=str(e))
        finally:
            if proc.returncode is None:
                proc.terminate()

    def parse_usage(self, raw_data: dict) -> dict:
        return {
            "input_tokens": raw_data.get("input_tokens", 0),
            "output_tokens": raw_data.get("output_tokens", 0),
            "cache_read": raw_data.get("cache_read_input_tokens", 0),
            "cache_write": raw_data.get("cache_creation_input_tokens", 0),
        }
