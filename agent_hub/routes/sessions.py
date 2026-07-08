"""/api/sessions 路由"""

from fastapi import APIRouter, Query, HTTPException

from ..session_store import (
    list_sessions,
    get_session,
    get_messages,
    delete_session,
)

router = APIRouter()


@router.get("/sessions")
async def list_sessions_route(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    engine: str = Query(""),
):
    sessions = list_sessions(limit=limit, offset=offset, engine=engine or "")
    return {
        "sessions": [
            {
                "id": s["id"],
                "engine": s["engine"],
                "model": s["model"],
                "title": s["title"],
                "status": s["status"],
                "message_count": s["message_count"],
                "total_input_tokens": s["total_input_tokens"],
                "total_output_tokens": s["total_output_tokens"],
                "cwd": s["cwd"],
                "team_mode": s["team_mode"] if "team_mode" in s.keys() else "serial",
                "team_config": s["team_config"] if "team_config" in s.keys() else "{}",
                "updated_at": s["updated_at"],
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@router.get("/sessions/{session_id}")
async def get_session_route(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = get_messages(session_id)
    return {
        "session": session,
        "messages": [
            {
                "id": m["id"],
                "role": m["role"],
                "type": m["type"],
                "content": m["content"],
                "tool_name": m["tool_name"],
                "tool_input": m["tool_input"],
                "token_input": m["token_input"],
                "token_output": m["token_output"],
                "sequence": m["sequence"],
                "engine_name": m["engine_name"] or "",
                "created_at": m["created_at"],
            }
            for m in messages
        ],
    }


@router.delete("/sessions/{session_id}")
async def delete_session_route(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    delete_session(session_id)
    return {"ok": True, "deleted": session_id}
