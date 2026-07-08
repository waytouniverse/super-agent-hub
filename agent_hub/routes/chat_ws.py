"""/ws/chat WebSocket 路由 - 核心聊天通道"""

import asyncio
import json
import os
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..adapters.claude import ClaudeAdapter
from ..adapters.codex import CodexAdapter
from ..adapters.hermes import HermesAdapter
from ..session_store import (
    create_session,
    get_session,
    get_messages,
    insert_message,
    update_message_content,
    update_session,
    insert_token_event,
)
from ..stats import estimate_cost
from ..config import load

router = APIRouter()

ADAPTER_MAP = {
    "claude": ClaudeAdapter,
    "codex": CodexAdapter,
    "hermes": HermesAdapter,
}

AGENT_HUB_RUNTIME_NOTES = [
    "Agent Hub 运行约束：",
    "- 不要使用 Read 工具读取图片、视频、PDF、压缩包或其他二进制文件（例如 .png、.jpg、.jpeg、.gif、.webp、.pdf、.zip）。需要检查这类文件时，用 Bash 的 ls -lh/file 获取元信息，或直接把本地文件路径返回给用户。",
    "- 如果需要向用户展示本地图片，请使用 Markdown 图片语法：![说明](/absolute/path.png)。",
    "",
]


def _build_context_prompt(prompt: str, messages: list[dict]) -> str:
    lines = AGENT_HUB_RUNTIME_NOTES.copy()

    if messages:
        lines.extend([
            "以下是当前 Agent Hub 会话中最近的历史上下文。请把它当作同一个连续对话来理解。",
            "",
        ])
        for msg in messages[-20:]:
            role = "用户" if msg.get("role") == "user" else "助手"
            msg_type = msg.get("type", "text")
            if msg_type == "tool_call":
                tool = msg.get("tool_name") or "tool"
                tool_input = msg.get("tool_input") or ""
                if len(tool_input) > 1200:
                    tool_input = tool_input[:1200] + "...[已截断]"
                lines.append(f"{role}调用工具 {tool}: {tool_input}")
                continue

            content = msg.get("content") or ""
            if len(content) > 1500:
                content = content[:1500] + "...[已截断]"
            if content:
                lines.append(f"{role}: {content}")

    lines.extend([
        "",
        "现在用户的新消息是：",
        prompt,
    ])
    return "\n".join(lines)


async def _persist_and_send(
    ws: WebSocket,
    session_id: str,
    sequence: int,
    role: str,
    msg_type: str,
    content: str = "",
    tool_name: str = "",
    tool_input: str = "",
) -> int:
    """写入SQLite并发送到前端，返回sequence"""
    insert_message(
        session_id=session_id,
        role=role,
        msg_type=msg_type,
        content=content,
        tool_name=tool_name,
        tool_input=tool_input,
        sequence=sequence,
    )
    await ws.send_json({
        "type": msg_type,
        "role": role,
        "content": content,
        "tool": tool_name,
        "input": tool_input,
        "sequence": sequence,
    })
    return sequence + 1


@router.websocket("/ws/chat/{engine}")
async def chat_websocket(ws: WebSocket, engine: str):
    await ws.accept()

    if engine not in ADAPTER_MAP:
        await ws.send_json({"type": "error", "content": f"不支持的引擎: {engine}"})
        await ws.close()
        return

    config = load()
    engine_config = config.get("engines", {}).get(engine, {})

    from ..detector import detect_one
    engine_info = detect_one(engine)
    if not engine_info or not engine_info.installed:
        await ws.send_json({
            "type": "error",
            "content": f"{engine_info.display_name if engine_info else engine} 未安装或不可用",
        })
        await ws.close()
        return

    # 使用检测到的实际模型
    detected_model = engine_info.models[0] if engine_info.models else ""
    effective_model = engine_config.get("model") or detected_model

    adapter_cls = ADAPTER_MAP[engine]
    adapter = adapter_cls(engine_info.executable, engine_config.copy())
    active_session_id = ""
    active_sequence = 0
    active_completed = True
    active_has_response = False

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "content": "无效的JSON格式"})
                continue

            prompt = data.get("prompt", "")
            resume_session = data.get("resume_session", "")
            cwd = data.get("cwd", os.getcwd())
            permission_mode = data.get("permission_mode", "")
            allow_project_tools = bool(data.get("allow_project_tools", False))
            if not cwd or not os.path.isdir(os.path.expanduser(cwd)):
                await ws.send_json({"type": "error", "content": "项目目录不存在或不可用"})
                continue
            cwd = os.path.abspath(os.path.expanduser(cwd))
            if permission_mode in {"default", "acceptEdits", "auto", "bypassPermissions", "dontAsk", "plan"}:
                adapter.config["permission_mode"] = permission_mode
            adapter.config["allowed_tools"] = (
                ["Read", "Write", "Edit", "MultiEdit", "Glob", "Grep", "LS", "Bash"]
                if allow_project_tools else []
            )

            if not prompt.strip():
                await ws.send_json({"type": "error", "content": "prompt 不能为空"})
                continue

            # 处理会话
            session_id = resume_session
            if session_id:
                existing = get_session(session_id)
                if not existing:
                    await ws.send_json({"type": "error", "content": "会话不存在"})
                    continue
            else:
                title = prompt[:80] + ("..." if len(prompt) > 80 else "")
                session_id = create_session(
                    engine=engine,
                    model=effective_model,
                    cwd=cwd,
                    title=title,
                )
                await ws.send_json({
                    "type": "session_created",
                    "session_id": session_id,
                    "title": title,
                })

            # 计算已有消息数作为 sequence 起点
            existing_messages = get_messages(session_id) if resume_session else []
            seq = len(existing_messages) + 1

            # 保存用户消息（静默写入DB，不回传前端）
            insert_message(
                session_id=session_id,
                role="user",
                msg_type="text",
                content=prompt,
                sequence=seq,
            )
            seq += 1
            active_session_id = session_id
            active_sequence = seq
            active_completed = False
            active_has_response = False
            update_session(session_id, status="running")

            # 启动Agent子进程 + 流式输出
            accumulated_text: list[str] = []
            assistant_message_id: int | None = None
            final_usage = {}
            agent_prompt = _build_context_prompt(prompt, existing_messages)

            try:
                async for chunk in adapter.chat_stream(agent_prompt, session_id, cwd):
                    if chunk.type == "text":
                        accumulated_text.append(chunk.data.get("content", ""))
                        full_text = "".join(accumulated_text)
                        if assistant_message_id is None:
                            assistant_message_id = insert_message(
                                session_id=session_id,
                                role="assistant",
                                msg_type="text",
                                content=full_text,
                                sequence=seq,
                            )
                            seq += 1
                            active_sequence = seq
                        else:
                            update_message_content(assistant_message_id, full_text)
                        active_has_response = True
                        await ws.send_json({
                            "type": "text_stream",
                            "role": "assistant",
                            "content": chunk.data["content"],
                        })

                    elif chunk.type == "tool_call":
                        insert_message(
                            session_id=session_id,
                            role="assistant",
                            msg_type="tool_call",
                            tool_name=chunk.data.get("tool", ""),
                            tool_input=json.dumps(chunk.data.get("input", {}), ensure_ascii=False),
                            sequence=seq,
                        )
                        seq += 1
                        active_sequence = seq
                        active_has_response = True
                        await ws.send_json({
                            "type": "tool_call",
                            "tool": chunk.data.get("tool", ""),
                            "input": json.dumps(chunk.data.get("input", {}), ensure_ascii=False),
                        })

                    elif chunk.type == "tool_result":
                        await ws.send_json({
                            "type": "tool_result",
                            "content": chunk.data.get("content", ""),
                        })

                    elif chunk.type == "done":
                        final_usage = chunk.data
                        active_completed = True
                        break

                    elif chunk.type == "error":
                        error_content = chunk.data.get("content", "")
                        if accumulated_text and assistant_message_id is not None:
                            update_message_content(assistant_message_id, "".join(accumulated_text))
                        elif error_content:
                            insert_message(
                                session_id=session_id,
                                role="assistant",
                                msg_type="text",
                                content=f"*错误: {error_content}*",
                                sequence=seq,
                            )
                            seq += 1
                            active_sequence = seq
                            active_has_response = True
                        active_completed = True
                        await ws.send_json({"type": "error", "content": error_content})
                        break

            except asyncio.CancelledError:
                insert_message(
                    session_id=session_id,
                    role="assistant",
                    msg_type="text",
                    content="*任务被取消，未完成。*",
                    sequence=seq,
                )
                update_session(session_id, status="interrupted")
                active_completed = True
                try:
                    await ws.send_json({"type": "error", "content": "任务被取消"})
                except Exception:
                    pass
                break

            # 更新 token 统计
            if final_usage:
                input_t = final_usage.get("input_tokens", 0)
                output_t = final_usage.get("output_tokens", 0)
                cache_r = final_usage.get("cache_read", 0)
                cache_w = final_usage.get("cache_write", 0)
                model = final_usage.get("model") or effective_model
                cost = estimate_cost(input_t, output_t, cache_r, cache_w, model)

                update_session(
                    session_id,
                    total_input_tokens=input_t,
                    total_output_tokens=output_t,
                    total_cache_read=cache_r,
                    total_cache_write=cache_w,
                    total_cost_usd=round(cost, 6),
                )
                insert_token_event(
                    session_id, model,
                    input_tokens=input_t,
                    output_tokens=output_t,
                    cache_read=cache_r,
                    cache_write=cache_w,
                    cost_usd=round(cost, 6),
                )

            cost_cny = round(estimate_cost(
                    final_usage.get("input_tokens", 0),
                    final_usage.get("output_tokens", 0),
                    final_usage.get("cache_read", 0),
                    final_usage.get("cache_write", 0),
                    final_usage.get("model", ""),
                ) * 7.2, 4)
            final_usage["cost_cny"] = cost_cny

            await ws.send_json({
                "type": "done",
                "session_id": session_id,
                "usage": final_usage,
            })
            active_completed = True
            active_session_id = ""
            active_sequence = 0
            active_has_response = False
            update_session(session_id, status="active")

    except WebSocketDisconnect:
        if active_session_id and not active_completed:
            insert_message(
                session_id=active_session_id,
                role="assistant",
                msg_type="text",
                content="*任务连接已中断，未完成。请重新发送或继续执行。*",
                sequence=active_sequence,
            )
            update_session(active_session_id, status="interrupted")
    except Exception as e:
        if active_session_id and not active_completed:
            insert_message(
                session_id=active_session_id,
                role="assistant",
                msg_type="text",
                content=f"*任务异常中断: {e}*",
                sequence=active_sequence,
            )
            update_session(active_session_id, status="interrupted")
        try:
            await ws.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
