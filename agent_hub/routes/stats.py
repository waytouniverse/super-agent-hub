"""/api/stats 路由"""

from fastapi import APIRouter, Query

from ..session_store import get_token_stats
from ..stats import get_daily_stats, format_number, estimate_cost, USD_TO_CNY

router = APIRouter()


@router.get("/stats")
async def stats_overview(days: int = Query(7, ge=1, le=365)):
    raw = get_token_stats(days=days)
    daily = get_daily_stats(days=days)

    return {
        "period_days": days,
        "summary": {
            "total_tokens": (
                raw["total_input"] + raw["total_output"]
                + raw["total_cache_read"] + raw["total_cache_write"]
            ),
            "total_input": raw["total_input"],
            "total_output": raw["total_output"],
            "total_cache_read": raw["total_cache_read"],
            "total_cache_write": raw["total_cache_write"],
            "total_cost_usd": round(raw["total_cost"], 2),
            "total_cost_cny": round(raw["total_cost"] * USD_TO_CNY, 2),
            "total_events": raw["total_events"],
            "display_tokens": format_number(
                raw["total_input"] + raw["total_output"]
                + raw["total_cache_read"] + raw["total_cache_write"]
            ),
        },
        "by_model": raw["by_model"],
        "daily_trend": [
            {
                "day": d["day"],
                "tokens": (d["input_t"] or 0) + (d["output_t"] or 0)
                + (d["cache_r"] or 0) + (d["cache_w"] or 0),
                "sessions": d["sessions"],
                "events": d["events"],
            }
            for d in daily
        ],
    }


@router.get("/stats/daily")
async def stats_daily(days: int = Query(30, ge=1, le=365)):
    daily = get_daily_stats(days=days)
    return {
        "daily": [
            {
                "day": d["day"],
                "input_tokens": d["input_t"] or 0,
                "output_tokens": d["output_t"] or 0,
                "cache_read": d["cache_r"] or 0,
                "cache_write": d["cache_w"] or 0,
                "cost_usd": round(d["cost"] or 0, 4),
                "sessions": d["sessions"],
                "events": d["events"],
            }
            for d in daily
        ]
    }
