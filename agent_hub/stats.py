"""Token统计（复用 token-monitor 定价逻辑）"""

from pathlib import Path
from collections import defaultdict
from typing import Optional

from .session_store import _get_conn

# 复用 token-monitor 的定价模型
PRICING = {
    # Anthropic Claude
    "claude-opus-4-7": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 15.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0, "cache_read": 0.1, "cache_write": 1.0},
    # OpenAI Codex
    "gpt-5-codex": {"input": 5.0, "output": 15.0, "cache_read": 2.5, "cache_write": 5.0},
    "gpt-5.1-codex": {"input": 5.0, "output": 15.0, "cache_read": 2.5, "cache_write": 5.0},
    # DeepSeek
    "DeepSeek-V4-Pro": {"input": 0.27, "output": 1.10, "cache_read": 0.07, "cache_write": 0.27},
    "deepseek-v4-pro": {"input": 0.27, "output": 1.10, "cache_read": 0.07, "cache_write": 0.27},
    "DeepSeek-V3": {"input": 0.27, "output": 1.10, "cache_read": 0.07, "cache_write": 0.27},
}

USD_TO_CNY = 7.2


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    cache_read: int = 0,
    cache_write: int = 0,
    model: str = "claude-sonnet-4-6",
) -> float:
    pricing = PRICING.get(model, {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.0})
    cost = (
        input_tokens / 1_000_000 * pricing["input"]
        + output_tokens / 1_000_000 * pricing["output"]
        + cache_read / 1_000_000 * pricing["cache_read"]
        + cache_write / 1_000_000 * pricing["cache_write"]
    )
    return cost


def format_number(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    elif n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def get_daily_stats(days: int = 7) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        """SELECT date(created_at) as day,
                  SUM(input_tokens) as input_t,
                  SUM(output_tokens) as output_t,
                  SUM(cache_read_tokens) as cache_r,
                  SUM(cache_creation_tokens) as cache_w,
                  SUM(cost_usd) as cost,
                  COUNT(DISTINCT session_id) as sessions,
                  COUNT(*) as events
           FROM token_events
           WHERE created_at >= datetime('now', ? || ' days')
           GROUP BY day
           ORDER BY day ASC""",
        (f"-{days}",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
