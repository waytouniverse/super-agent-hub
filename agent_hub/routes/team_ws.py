"""/ws/chat/team WebSocket 路由 - 多引擎团队对话（串行/并行/辩论/会诊）"""

import asyncio
import json
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..orchestrator import create_orchestrator, ADAPTER_MAP, ENGINE_DISPLAY
from ..orchestrator.task_plan import Plan
from ..session_store import (
    create_session,
    get_messages,
    insert_message,
    update_message_content,
    update_session,
    insert_token_event,
)
from ..stats import estimate_cost
from ..config import load

router = APIRouter()


@router.websocket("/ws/chat/team")
async def team_chat_websocket(ws: WebSocket):
    await ws.accept()

    config = load()

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "content": "无效的JSON格式"})
                continue

            msg_type = data.get("type", "")

            # 会诊模式的双向消息在 orchestrator 运行期间处理
            if msg_type == "plan_confirmed" or msg_type == "stop":
                await ws.send_json({"type": "error", "content": "当前不在对话中，请先发送 prompt"})
                continue

            prompt = data.get("prompt", "")
            engines = data.get("engines", [])
            mode = data.get("mode", "serial")
            mode_config = data.get("mode_config", {})
            cwd = data.get("cwd", os.getcwd())
            permission_mode = data.get("permission_mode", "")

            if not cwd or not os.path.isdir(os.path.expanduser(cwd)):
                await ws.send_json({"type": "error", "content": "项目目录不存在"})
                continue
            cwd = os.path.abspath(os.path.expanduser(cwd))

            if not prompt.strip():
                await ws.send_json({"type": "error", "content": "prompt 不能为空"})
                continue

            if not engines or len(engines) < 2:
                await ws.send_json({"type": "error", "content": "请至少选择 2 个引擎"})
                continue

            # 验证引擎
            valid_engines = []
            for e in engines:
                if e in ADAPTER_MAP:
                    valid_engines.append(e)
                else:
                    await ws.send_json({"type": "error", "content": f"不支持的引擎: {e}"})
            if len(valid_engines) < 2:
                await ws.send_json({"type": "error", "content": "至少需要 2 个有效引擎"})
                continue

            # 验证模式
            if mode not in ("serial", "parallel", "debate", "consultation"):
                await ws.send_json({"type": "error", "content": f"不支持的模式: {mode}"})
                continue

            # 创建会话
            title = prompt[:80] + ("..." if len(prompt) > 80 else "")
            team_config = {
                "mode": mode,
                "engines": valid_engines,
                "cwd": cwd,
            }
            if mode in ("debate", "consultation"):
                team_config["max_rounds"] = mode_config.get("max_rounds", 3)
                team_config["judge_engine"] = mode_config.get("judge_engine", "")

            session_id = create_session(
                engine="team",
                model=", ".join(valid_engines),
                cwd=cwd,
                title=title,
                team_mode=mode,
                team_config=json.dumps(team_config, ensure_ascii=False),
            )
            await ws.send_json({
                "type": "session_created",
                "session_id": session_id,
                "title": title,
                "engines": valid_engines,
                "mode": mode,
            })

            # 保存用户消息
            existing = get_messages(session_id)
            seq = len(existing) + 1
            insert_message(
                session_id=session_id,
                role="user",
                msg_type="text",
                content=prompt,
                sequence=seq,
            )
            seq += 1
            update_session(session_id, status="running")

            # 每个引擎的流式消息 ID
            engine_msg_ids: dict[str, int | None] = {
                e: None for e in valid_engines
            }

            async def handle_event(event: dict):
                nonlocal seq

                evt_type = event.get("type", "")
                eng = event.get("engine", "")
                phase = event.get("phase", "")
                round_num = event.get("round", 0)

                if evt_type == "engine_start":
                    engine_msg_ids[eng] = None
                    await ws.send_json({
                        "type": "engine_start",
                        "engine": eng,
                        "display": event.get("display", eng),
                        "phase": phase,
                        "round": round_num,
                    })

                elif evt_type == "text_stream":
                    content = event.get("content", "")
                    if engine_msg_ids.get(eng) is None:
                        mid = insert_message(
                            session_id=session_id,
                            role="assistant",
                            msg_type="text",
                            content=content,
                            sequence=seq,
                            engine_name=eng,
                            phase=phase,
                            round_num=round_num,
                        )
                        engine_msg_ids[eng] = mid
                        seq += 1
                    else:
                        update_message_content(engine_msg_ids[eng], content)
                    await ws.send_json({
                        "type": "text_stream",
                        "engine": eng,
                        "content": content,
                        "phase": phase,
                        "round": round_num,
                    })

                elif evt_type == "tool_call":
                    insert_message(
                        session_id=session_id,
                        role="assistant",
                        msg_type="tool_call",
                        tool_name=event.get("tool", ""),
                        tool_input=json.dumps(event.get("input", {}), ensure_ascii=False),
                        sequence=seq,
                        engine_name=eng,
                        phase=phase,
                        round_num=round_num,
                    )
                    seq += 1
                    await ws.send_json({
                        "type": "tool_call",
                        "engine": eng,
                        "tool": event.get("tool", ""),
                        "input": json.dumps(event.get("input", {}), ensure_ascii=False),
                        "phase": phase,
                        "round": round_num,
                    })

                elif evt_type == "engine_done":
                    engine_msg_ids[eng] = None
                    await ws.send_json({
                        "type": "engine_done",
                        "engine": eng,
                        "usage": event.get("usage", {}),
                        "phase": phase,
                        "round": round_num,
                    })

                elif evt_type == "error":
                    await ws.send_json({
                        "type": "error",
                        "engine": eng,
                        "content": event.get("content", ""),
                    })

                elif evt_type in ("phase_start", "phase_end", "round_start", "round_end",
                                  "judge_decision", "plan_generated"):
                    # 持久化上下文事件（使用前端兼容的类型名）
                    ctx_type = evt_type
                    ctx_content = ""
                    if evt_type == "round_start":
                        ctx_type = "round_separator"
                        ctx_content = f"第 {event.get('round', '')} 轮讨论"
                    elif evt_type == "judge_decision":
                        ctx_type = "judge"
                        ctx_content = json.dumps({
                            "decision": event.get("decision", ""),
                            "evaluation": event.get("evaluation", ""),
                            "final_summary": event.get("final_summary", ""),
                        }, ensure_ascii=False)

                    if ctx_content:
                        insert_message(
                            session_id=session_id,
                            role="system",
                            msg_type=ctx_type,
                            content=ctx_content,
                            sequence=seq,
                            phase=event.get("phase", ""),
                            round_num=event.get("round", 0),
                        )
                        seq += 1
                    await ws.send_json(event)

                elif evt_type in ("task_start", "task_done", "task_error"):
                    # 持久化任务事件
                    insert_message(
                        session_id=session_id,
                        role="system",
                        msg_type=evt_type,
                        content=json.dumps({
                            "task_id": event.get("task_id", ""),
                            "title": event.get("title", ""),
                            "engine": event.get("engine", ""),
                            "error": event.get("error", ""),
                        }, ensure_ascii=False),
                        sequence=seq,
                        phase="execution",
                    )
                    seq += 1
                    await ws.send_json(event)

            # 创建编排器并运行
            orchestrator_config = config.copy()
            if mode in ("debate", "consultation"):
                orchestrator_config["max_rounds"] = mode_config.get("max_rounds", 3)
                orchestrator_config["judge_engine"] = mode_config.get("judge_engine", "")
            if permission_mode:
                orchestrator_config["permission_mode"] = permission_mode

            orchestrator = create_orchestrator(
                mode=mode,
                engines=valid_engines,
                cwd=cwd,
                config=orchestrator_config,
            )

            try:
                usages = await orchestrator.run(prompt, handle_event)
            except Exception as e:
                await ws.send_json({"type": "error", "content": str(e)})
                update_session(session_id, status="interrupted")
                break

            # 会诊模式：等待用户确认计划，然后执行任务
            if mode == "consultation" and hasattr(orchestrator, 'execute_tasks'):
                plan = orchestrator._last_plan if hasattr(orchestrator, '_last_plan') else None

                if plan:
                    # 等待用户确认
                    plan_confirmed = False
                    confirmed_plan = None
                    try:
                        raw = await asyncio.wait_for(ws.receive_text(), timeout=600)
                        data = json.loads(raw)
                        if data.get("type") == "plan_confirmed" and data.get("confirmed"):
                            plan_confirmed = True
                            confirmed_data = data.get("plan", {})
                            if confirmed_data.get("tasks"):
                                from ..orchestrator.task_plan import Plan as PlanCls
                                confirmed_plan = PlanCls.from_dict(confirmed_data)
                    except asyncio.TimeoutError:
                        pass

                    if plan_confirmed and confirmed_plan:
                        try:
                            exec_usages = await orchestrator.execute_tasks(confirmed_plan, handle_event)
                            usages.extend(exec_usages)
                        except Exception as e:
                            await ws.send_json({"type": "error", "content": f"任务执行失败: {str(e)}"})

            # 汇总 token 统计
            total_input = sum(u.get("input_tokens", 0) for u in usages)
            total_output = sum(u.get("output_tokens", 0) for u in usages)
            total_cache_read = sum(u.get("cache_read", 0) for u in usages)
            total_cache_write = sum(u.get("cache_write", 0) for u in usages)
            total_cost = estimate_cost(total_input, total_output, total_cache_read, total_cache_write, "claude-sonnet-4-6")

            update_session(
                session_id,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                total_cache_read=total_cache_read,
                total_cache_write=total_cache_write,
                total_cost_usd=round(total_cost, 6),
            )

            for u in usages:
                insert_token_event(
                    session_id,
                    u.get("model", ""),
                    input_tokens=u.get("input_tokens", 0),
                    output_tokens=u.get("output_tokens", 0),
                    cache_read=u.get("cache_read", 0),
                    cache_write=u.get("cache_write", 0),
                    cost_usd=round(estimate_cost(
                        u.get("input_tokens", 0),
                        u.get("output_tokens", 0),
                        u.get("cache_read", 0),
                        u.get("cache_write", 0),
                        u.get("model", "claude-sonnet-4-6"),
                    ), 6),
                )

            cost_cny = round(total_cost * 7.2, 4)
            await ws.send_json({
                "type": "done",
                "session_id": session_id,
                "mode": mode,
                "usage": {
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                    "cache_read": total_cache_read,
                    "cache_write": total_cache_write,
                    "cost_cny": cost_cny,
                },
                "engines_usage": usages,
            })

            update_session(session_id, status="active")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
