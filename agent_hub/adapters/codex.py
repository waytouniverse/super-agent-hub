"""Codex CLI adapter."""

import asyncio
import json
import os
import subprocess
import tomllib
from pathlib import Path
from typing import AsyncIterator

from .base import BaseAdapter, MessageChunk


TRANSIENT_TRANSPORT_MARKERS = (
    "Reconnecting...",
    "Falling back from WebSockets to HTTPS transport",
    "stream disconnected before completion",
    "Connection reset by peer",
)


def _detect_macos_proxy() -> str | None:
    """读取 macOS 系统代理设置，返回 https_proxy 值"""
    try:
        result = subprocess.run(
            ["scutil", "--proxy"],
            capture_output=True, text=True, timeout=3,
        )
        https_enable = False
        https_host = ""
        https_port = ""
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line == "HTTPSEnable : 1":
                https_enable = True
            elif line.startswith("HTTPSProxy : "):
                https_host = line.split(" : ")[1]
            elif line.startswith("HTTPSPort : "):
                https_port = line.split(" : ")[1]
        if https_enable and https_host and https_port:
            return f"http://{https_host}:{https_port}"
    except Exception:
        pass
    return None


def _is_transient_transport_message(message: str) -> bool:
    return any(marker in message for marker in TRANSIENT_TRANSPORT_MARKERS)


class CodexAdapter(BaseAdapter):
    """Run `codex exec --json` and normalize its JSONL events."""

    def build_command(self, prompt: str, session_id: str, cwd: str = None) -> list[str]:
        cmd = [
            self.executable,
            "exec",
            "--json",
            "--color", "never",
            "--skip-git-repo-check",
        ]

        model = self.config.get("model")
        if model:
            cmd.extend(["--model", model])

        allow_project_tools = bool(self.config.get("allowed_tools"))
        sandbox = "workspace-write" if allow_project_tools else "read-only"
        cmd.extend(["--sandbox", sandbox])
        cmd.extend(["-c", "approval_policy=never"])

        if cwd:
            cmd.extend(["--cd", cwd])

        cmd.append(prompt)
        return cmd

    async def chat_stream(
        self, prompt: str, session_id: str, cwd: str = None
    ) -> AsyncIterator[MessageChunk]:
        cmd = self.build_command(prompt, session_id, cwd)
        env = os.environ.copy()
        env.setdefault("CODEX_HOME", os.path.expanduser("~/.codex"))
        env.update(self._load_codex_shell_env(env["CODEX_HOME"]))

        # 自动注入 macOS 系统代理，解决子进程不继承系统代理的问题
        if not env.get("HTTPS_PROXY") and not env.get("https_proxy"):
            proxy = _detect_macos_proxy()
            if proxy:
                env["HTTPS_PROXY"] = proxy
                env["https_proxy"] = proxy

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
            cwd=cwd,
            env=env,
        )

        final_usage: dict = {}

        try:
            async for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    if _is_transient_transport_message(line):
                        continue
                    yield MessageChunk("text", content=line + "\n")
                    continue

                chunk = self._event_to_chunk(event)
                if chunk:
                    if chunk.type == "done":
                        final_usage = chunk.data
                    else:
                        yield chunk

            return_code = await proc.wait()
            if return_code != 0:
                stderr = ""
                if proc.stderr:
                    stderr = (await proc.stderr.read()).decode("utf-8", errors="replace").strip()
                if stderr and _is_transient_transport_message(stderr):
                    yield MessageChunk("error", content=stderr)
                    return
                yield MessageChunk(
                    "error",
                    content=stderr or f"Codex CLI 退出，状态码 {return_code}",
                )
                return

            yield MessageChunk("done", **final_usage)

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

    def _event_to_chunk(self, event: dict) -> MessageChunk | None:
        event_type = event.get("type", "")

        if event_type in {"thread.started", "turn.started"}:
            return None

        if event_type == "turn.completed":
            usage = event.get("usage") or event.get("token_usage") or {}
            parsed = self.parse_usage(usage)
            model = event.get("model") or event.get("model_name") or self.config.get("model") or "gpt-5-codex"
            return MessageChunk("done", **parsed, model=model)

        if event_type == "error":
            message = event.get("message", "")
            if _is_transient_transport_message(message):
                return None
            return MessageChunk("error", content=message or "Codex CLI 出错")

        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        item_type = item.get("type", "")

        if event_type in {"item.started", "item.completed"}:
            if item_type in {"message", "assistant_message", "agent_message"}:
                content = self._extract_text(item)
                if content:
                    return MessageChunk("text", content=content)

            if item_type in {"command_execution", "tool_call", "function_call"}:
                return MessageChunk(
                    "tool_call",
                    tool=item.get("name") or item.get("command") or "Codex",
                    input=self._extract_tool_input(item),
                )

            if item_type == "error":
                message = item.get("message", "")
                if message and "skills context budget" not in message:
                    return MessageChunk("error", content=message)

        usage = event.get("usage") or event.get("token_usage")
        if usage:
            parsed = self.parse_usage(usage)
            model = event.get("model") or event.get("model_name") or self.config.get("model") or "gpt-5-codex"
            return MessageChunk("done", **parsed, model=model)

        return None

    def _extract_text(self, item: dict) -> str:
        content = item.get("content") or item.get("text") or item.get("message") or ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    text = block.get("text") or block.get("content")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return ""

    def _extract_tool_input(self, item: dict) -> dict:
        if isinstance(item.get("input"), dict):
            return item["input"]
        command = item.get("command")
        if command:
            return {"command": command}
        return {k: v for k, v in item.items() if k not in {"id", "type"}}

    def _load_codex_shell_env(self, codex_home: str) -> dict[str, str]:
        config_path = Path(codex_home).expanduser() / "config.toml"
        if not config_path.exists():
            return {}

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
        except Exception:
            return {}

        env_config = (
            config.get("shell_environment_policy", {})
            .get("set", {})
        )
        return {str(key): str(value) for key, value in env_config.items()}

    def parse_usage(self, raw_data: dict) -> dict:
        return {
            "input_tokens": raw_data.get("input_tokens", raw_data.get("input", 0)),
            "output_tokens": raw_data.get("output_tokens", raw_data.get("output", 0)),
            "cache_read": raw_data.get("cache_read_input_tokens", raw_data.get("cache_read", 0)),
            "cache_write": raw_data.get("cache_creation_input_tokens", raw_data.get("cache_write", 0)),
        }
