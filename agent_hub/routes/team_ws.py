"""/ws/chat/team WebSocket 路由 - 多引擎团队对话（串行/并行/辩论/会诊）"""

import asyncio
import json
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..orchestrator import create_orchestrator, ADAPTER_MAP, ENGINE_DISPLAY
from ..orchestrator.consultation import ConsultationOrchestrator, PLAN_SYSTEM_PROMPT
from ..orchestrator.task_plan import Plan, TaskPlan, parse_plan_from_text
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


def _build_context_prompt(prompt: str, messages: list[dict]) -> str:
    if not messages:
        return prompt

    lines = [
        "以下是当前 Agent Hub 团队模式会话中最近的历史上下文。请把它当作同一个连续讨论来理解。",
        "",
    ]
    for msg in messages[-30:]:
        role = msg.get("role", "")
        msg_type = msg.get("type", "text")
        engine_name = msg.get("engine_name") or ""

        if role == "system" or msg_type in {
            "judge",
            "round_separator",
            "phase_start",
            "phase_end",
            "round_start",
            "round_end",
            "task_start",
            "task_done",
            "task_error",
            "plan_generated",
        }:
            continue

        if msg_type == "tool_call":
            tool = msg.get("tool_name") or "tool"
            tool_input = msg.get("tool_input") or ""
            if len(tool_input) > 1200:
                tool_input = tool_input[:1200] + "...[已截断]"
            speaker = f"助手({engine_name})" if engine_name else "助手"
            lines.append(f"{speaker}调用工具 {tool}: {tool_input}")
            continue

        content = msg.get("content") or ""
        if not content:
            continue
        if len(content) > 1800:
            content = content[:1800] + "...[已截断]"

        if role == "user":
            speaker = "用户"
        elif role == "assistant":
            speaker = f"助手({engine_name})" if engine_name else "助手"
        elif role == "system":
            speaker = "系统"
        else:
            speaker = role or "消息"
        lines.append(f"{speaker}: {content}")

    lines.extend([
        "",
        "现在用户的新消息是：",
        prompt,
    ])
    return "\n".join(lines)


def _build_plan_prompt(user_prompt: str, discussion_results: list[dict], allowed_engines: list[str]) -> str:
    lines = [
        PLAN_SYSTEM_PROMPT,
        "",
        "原始用户需求：",
        user_prompt,
        "",
        f"可分配执行任务的引擎只能从这些值中选择：{', '.join(allowed_engines)}",
        "",
        "团队讨论结果：",
    ]
    for result in discussion_results:
        engine = result.get("engine", "")
        content = result.get("content", "")
        if not content:
            continue
        display = ENGINE_DISPLAY.get(engine, engine or "unknown")
        if len(content) > 4000:
            content = content[:4000] + "\n...[内容已截断]"
        lines.extend([
            "",
            f"### {display}",
            content,
        ])
    lines.extend([
        "",
        "请基于以上讨论生成可执行的行动计划。不要只总结观点，必须拆成可执行、可验证的任务。",
    ])
    return "\n".join(lines)


def _ensure_executable_plan(
    plan: Plan,
    user_prompt: str,
    default_engine: str,
    allowed_engines: list[str],
) -> Plan:
    if plan.tasks:
        for task in plan.tasks:
            if not task.engine or task.engine not in allowed_engines:
                task.engine = default_engine
        return plan
    return Plan(
        summary=plan.summary or "团队已完成讨论，但未能解析出结构化任务，已创建兜底执行任务。",
        tasks=[
            TaskPlan(
                id="task-1",
                title="执行用户需求",
                description=f"根据团队讨论结果执行用户需求，并给出可验证的完成结果。\n\n用户需求：{user_prompt}",
                engine=default_engine,
                estimated_tool_calls=["Read", "Write", "Edit", "Bash"],
            )
        ],
    )


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
            resume_session = data.get("resume_session", "")

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

            existing_messages = []
            if resume_session:
                existing_session = get_session(resume_session)
                if not existing_session:
                    await ws.send_json({"type": "error", "content": "会话不存在"})
                    continue
                if existing_session.get("engine") != "team":
                    await ws.send_json({"type": "error", "content": "不是团队模式会话"})
                    continue
                session_id = resume_session
                title = existing_session.get("title") or prompt[:80]
                existing_messages = get_messages(session_id)
            else:
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
            seq = len(existing_messages) + 1
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
            engine_text_buffers: dict[str, str] = {
                e: "" for e in valid_engines
            }

            async def handle_event(event: dict):
                nonlocal seq

                evt_type = event.get("type", "")
                eng = event.get("engine", "")
                phase = event.get("phase", "")
                round_num = event.get("round", 0)

                if evt_type == "engine_start":
                    engine_msg_ids[eng] = None
                    engine_text_buffers[eng] = ""
                    await ws.send_json({
                        "type": "engine_start",
                        "engine": eng,
                        "display": event.get("display", eng),
                        "phase": phase,
                        "round": round_num,
                    })

                elif evt_type == "text_stream":
                    content = event.get("content", "")
                    engine_text_buffers[eng] = engine_text_buffers.get(eng, "") + content
                    full_content = engine_text_buffers[eng]
                    if engine_msg_ids.get(eng) is None:
                        mid = insert_message(
                            session_id=session_id,
                            role="assistant",
                            msg_type="text",
                            content=full_content,
                            sequence=seq,
                            engine_name=eng,
                            phase=phase,
                            round_num=round_num,
                        )
                        engine_msg_ids[eng] = mid
                        seq += 1
                    else:
                        update_message_content(engine_msg_ids[eng], full_content)
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
                    engine_text_buffers[eng] = ""
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
                    elif evt_type == "plan_generated":
                        ctx_content = json.dumps(
                            event.get("plan", {}), ensure_ascii=False
                        )
                    elif evt_type == "phase_start":
                        ctx_content = event.get("phase", "")

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

            agent_prompt = _build_context_prompt(prompt, existing_messages)

            try:
                usages = await orchestrator.run(agent_prompt, handle_event)
            except Exception as e:
                await ws.send_json({"type": "error", "content": str(e)})
                update_session(session_id, status="interrupted")
                break

            # 所有团队模式：讨论结束后必须进入计划确认，再执行任务
            executor = ConsultationOrchestrator(valid_engines, cwd, orchestrator_config)
            plan = getattr(orchestrator, "_last_plan", None)
            if plan is not None:
                plan = _ensure_executable_plan(plan, agent_prompt, valid_engines[0], valid_engines)
            if plan is None:
                await handle_event({"type": "phase_start", "phase": "planning"})
                plan_engine = orchestrator_config.get("judge_engine") or valid_engines[0]
                plan_result = await executor._run_one_engine(
                    _build_plan_prompt(agent_prompt, usages, valid_engines),
                    plan_engine,
                    handle_event,
                    phase="planning",
                )
                usages.append(plan_result)
                plan = _ensure_executable_plan(
                    parse_plan_from_text(plan_result.get("content", "")),
                    agent_prompt,
                    valid_engines[0],
                    valid_engines,
                )
                await handle_event({
                    "type": "plan_generated",
                    "plan": plan.to_dict(),
                    "summary": plan.summary,
                })
                await handle_event({"type": "phase_end", "phase": "planning"})

            if plan:
                plan_confirmed = False
                confirmed_plan = None
                try:
                    raw = await asyncio.wait_for(ws.receive_text(), timeout=600)
                    data = json.loads(raw)
                    if data.get("type") == "plan_confirmed" and data.get("confirmed"):
                        confirmed_data = data.get("plan", {})
                        if confirmed_data.get("tasks"):
                            plan_confirmed = True
                            confirmed_plan = _ensure_executable_plan(
                                Plan.from_dict(confirmed_data),
                                agent_prompt,
                                valid_engines[0],
                                valid_engines,
                            )
                except asyncio.TimeoutError:
                    pass
                except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
                    # 计划确认消息格式错误，跳过执行阶段但不中断整个会话
                    pass

                if plan_confirmed and confirmed_plan:
                    try:
                        executor.total_usage = []
                        exec_usages = await executor.execute_tasks(confirmed_plan, handle_event)
                        usages.extend(exec_usages)
                    except Exception as e:
                        await ws.send_json({"type": "error", "content": f"任务执行失败: {str(e)}"})

            # 汇总 token 统计
            total_input = sum(u.get("input_tokens", 0) for u in usages)
            total_output = sum(u.get("output_tokens", 0) for u in usages)
            total_cache_read = sum(u.get("cache_read", 0) for u in usages)
            total_cache_write = sum(u.get("cache_write", 0) for u in usages)
            # 按每个引擎各自的模型分别计价再求和，混合引擎场景才准确
            total_cost = sum(
                estimate_cost(
                    u.get("input_tokens", 0),
                    u.get("output_tokens", 0),
                    u.get("cache_read", 0),
                    u.get("cache_write", 0),
                    u.get("model") or "claude-sonnet-4-6",
                )
                for u in usages
            )

            # 累加到会话已有总量（多轮团队对话），而不是覆盖
            prev = get_session(session_id) or {}
            update_session(
                session_id,
                total_input_tokens=prev.get("total_input_tokens", 0) + total_input,
                total_output_tokens=prev.get("total_output_tokens", 0) + total_output,
                total_cache_read=prev.get("total_cache_read", 0) + total_cache_read,
                total_cache_write=prev.get("total_cache_write", 0) + total_cache_write,
                total_cost_usd=round((prev.get("total_cost_usd", 0) or 0) + total_cost, 6),
            )

            for u in usages:
                insert_token_event(
                    session_id,
                    u.get("model") or "other",
                    input_tokens=u.get("input_tokens", 0),
                    output_tokens=u.get("output_tokens", 0),
                    cache_read=u.get("cache_read", 0),
                    cache_write=u.get("cache_write", 0),
                    cost_usd=round(estimate_cost(
                        u.get("input_tokens", 0),
                        u.get("output_tokens", 0),
                        u.get("cache_read", 0),
                        u.get("cache_write", 0),
                        u.get("model") or "claude-sonnet-4-6",
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
