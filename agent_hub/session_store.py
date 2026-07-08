"""SQLite 会话和消息存储"""

import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import CONFIG_DIR

DB_DIR = CONFIG_DIR / "data"
DB_PATH = DB_DIR / "sessions.db"


def _get_conn() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            engine TEXT NOT NULL,
            model TEXT,
            title TEXT,
            status TEXT DEFAULT 'active',
            agent_session_id TEXT,
            cwd TEXT,
            team_mode TEXT DEFAULT 'serial',
            team_config TEXT DEFAULT '{}',
            total_input_tokens INTEGER DEFAULT 0,
            total_output_tokens INTEGER DEFAULT 0,
            total_cache_read INTEGER DEFAULT 0,
            total_cache_write INTEGER DEFAULT 0,
            total_cost_usd REAL DEFAULT 0,
            message_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            type TEXT NOT NULL,
            content TEXT,
            tool_name TEXT,
            tool_input TEXT,
            tool_output TEXT,
            token_input INTEGER DEFAULT 0,
            token_output INTEGER DEFAULT 0,
            sequence INTEGER NOT NULL,
            engine_name TEXT DEFAULT '',
            phase TEXT DEFAULT '',
            round INTEGER DEFAULT 0,
            plan TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, sequence);

        CREATE TABLE IF NOT EXISTS token_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id),
            model TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            cache_read_tokens INTEGER,
            cache_creation_tokens INTEGER,
            cost_usd REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    # 迁移：为已有表添加新列
    migrations = [
        "ALTER TABLE messages ADD COLUMN engine_name TEXT DEFAULT ''",
        "ALTER TABLE messages ADD COLUMN phase TEXT DEFAULT ''",
        "ALTER TABLE messages ADD COLUMN round INTEGER DEFAULT 0",
        "ALTER TABLE messages ADD COLUMN plan TEXT DEFAULT ''",
        "ALTER TABLE sessions ADD COLUMN team_mode TEXT DEFAULT 'serial'",
        "ALTER TABLE sessions ADD COLUMN team_config TEXT DEFAULT '{}'",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass
    conn.close()


def create_session(
    engine: str,
    model: str = "",
    cwd: str = "",
    title: str = "",
    agent_session_id: str = "",
    team_mode: str = "serial",
    team_config: str = "{}",
) -> str:
    session_id = str(uuid.uuid4())
    conn = _get_conn()
    conn.execute(
        """INSERT INTO sessions (id, engine, model, title, cwd, agent_session_id, team_mode, team_config)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, engine, model, title, cwd, agent_session_id, team_mode, team_config),
    )
    conn.commit()
    conn.close()
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_sessions(limit: int = 50, offset: int = 0, engine: str = "") -> list[dict]:
    conn = _get_conn()
    if engine:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE engine = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (engine, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_session(session_id: str, **kwargs) -> None:
    if not kwargs:
        return
    kwargs["updated_at"] = datetime.now().isoformat()
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [session_id]
    conn = _get_conn()
    conn.execute(f"UPDATE sessions SET {fields} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_session(session_id: str) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def insert_message(
    session_id: str,
    role: str,
    msg_type: str,
    content: str = "",
    tool_name: str = "",
    tool_input: str = "",
    tool_output: str = "",
    token_input: int = 0,
    token_output: int = 0,
    sequence: int = 0,
    engine_name: str = "",
    phase: str = "",
    round_num: int = 0,
    plan: str = "",
) -> int:
    conn = _get_conn()
    cursor = conn.execute(
        """INSERT INTO messages (session_id, role, type, content,
           tool_name, tool_input, tool_output,
           token_input, token_output, sequence, engine_name, phase, round, plan)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, role, msg_type, content,
         tool_name, tool_input, tool_output,
         token_input, token_output, sequence, engine_name, phase, round_num, plan),
    )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.execute(
        "UPDATE sessions SET message_count = message_count + 1, updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), session_id),
    )
    conn.commit()
    conn.close()
    return msg_id


def update_message_content(message_id: int, content: str) -> None:
    conn = _get_conn()
    conn.execute(
        "UPDATE messages SET content = ? WHERE id = ?",
        (content, message_id),
    )
    conn.commit()
    conn.close()


def get_messages(session_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY sequence ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_token_event(
    session_id: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read: int = 0,
    cache_write: int = 0,
    cost_usd: float = 0,
) -> None:
    conn = _get_conn()
    conn.execute(
        """INSERT INTO token_events (session_id, model,
           input_tokens, output_tokens, cache_read_tokens,
           cache_creation_tokens, cost_usd)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (session_id, model, input_tokens, output_tokens, cache_read, cache_write, cost_usd),
    )
    conn.commit()
    conn.close()


def get_token_stats(days: int = 7) -> dict:
    conn = _get_conn()
    rows = conn.execute(
        """SELECT session_id, model,
                  SUM(input_tokens) as total_input,
                  SUM(output_tokens) as total_output,
                  SUM(cache_read_tokens) as total_cache_read,
                  SUM(cache_creation_tokens) as total_cache_write,
                  SUM(cost_usd) as total_cost,
                  COUNT(*) as events
           FROM token_events
           WHERE created_at >= datetime('now', ? || ' days')
           GROUP BY session_id, model
           ORDER BY total_input DESC""",
        (f"-{days}",),
    ).fetchall()
    conn.close()

    result = {
        "total_input": 0,
        "total_output": 0,
        "total_cache_read": 0,
        "total_cache_write": 0,
        "total_cost": 0,
        "total_events": 0,
        "by_model": {},
        "by_session": [],
    }
    for row in rows:
        r = dict(row)
        result["total_input"] += r["total_input"]
        result["total_output"] += r["total_output"]
        result["total_cache_read"] += r["total_cache_read"]
        result["total_cache_write"] += r["total_cache_write"]
        result["total_cost"] += r["total_cost"]
        result["total_events"] += r["events"]

        model = r["model"] or "other"
        if model not in result["by_model"]:
            result["by_model"][model] = {"tokens": 0, "cost": 0}
        result["by_model"][model]["tokens"] += (
            r["total_input"] + r["total_output"] +
            r["total_cache_read"] + r["total_cache_write"]
        )
        result["by_model"][model]["cost"] += r["total_cost"]
        result["by_session"].append(r)

    return result
