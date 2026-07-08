"""会诊执行编排器 — 辩论→计划→确认→执行"""

import asyncio
from .base import BaseTeamOrchestrator, ENGINE_DISPLAY
from .debate import DebateOrchestrator
from .prompts import build_judge_prompt
from .judge import parse_judge_response
from .task_plan import Plan, parse_plan_from_text


PLAN_SYSTEM_PROMPT = """你是 AI 团队的**执行规划者**。团队已完成讨论，请根据讨论结果生成一份详细的行动计划。

请按以下 JSON 格式回复：
```json
{
  "summary": "讨论结论的简要总结",
  "tasks": [
    {
      "id": "task-1",
      "title": "任务标题",
      "description": "详细描述，包括具体要做什么、怎么验证",
      "engine": "claude",
      "estimated_tool_calls": ["Write", "Bash"]
    }
  ]
}
```

要求：
- 每个任务应该有明确的、可验证的产出
- engine 字段请指定最适合执行该任务的引擎（claude/codex/hermes）
- estimated_tool_calls 列出该任务可能会使用的工具类型
- 任务应该按执行顺序排列
- 每个任务应该是不可再分的原子操作"""


class ConsultationOrchestrator(BaseTeamOrchestrator):
    """会诊执行模式：辩论→生成计划→用户确认→自动执行"""

    def __init__(self, engines: list[str], cwd: str, config: dict):
        super().__init__(engines, cwd, config)
        self.max_rounds = config.get("max_rounds", 3)
        self.judge_engine = config.get("judge_engine", "")

    async def run(self, user_prompt: str, on_event) -> list[dict]:
        # Phase 1: 辩论
        debate = DebateOrchestrator(self.engines, self.cwd, {
            "max_rounds": self.max_rounds,
            "judge_engine": self.judge_engine,
        })
        await debate.run(user_prompt, on_event)
        self.total_usage = debate.total_usage

        # Phase 2: 生成计划
        await on_event({"type": "phase_start", "phase": "planning"})

        plan_engine = self.judge_engine or self.engines[0]
        plan_prompt = f"{PLAN_SYSTEM_PROMPT}\n\n原始用户需求：{user_prompt}\n\n请基于前面的讨论结果，生成行动计划。"

        plan_result = await self._run_one_engine(
            plan_prompt, plan_engine, on_event,
            phase="planning",
        )
        plan_content = plan_result.get("content", "")
        plan = parse_plan_from_text(plan_content)
        self._last_plan = plan  # 供 team_ws.py 访问

        await on_event({
            "type": "plan_generated",
            "plan": plan.to_dict(),
            "summary": plan.summary,
        })

        await on_event({"type": "phase_end", "phase": "planning"})

        # Phase 3: 等待用户确认 → 执行
        # 注意：确认信号通过 team_ws.py 中的双向通信机制传递
        # 这里返回 usage，执行在外部驱动
        return self.total_usage

    async def execute_tasks(self, plan: Plan, on_event) -> list[dict]:
        """执行已确认的任务列表"""
        await on_event({"type": "phase_start", "phase": "execution"})

        active_tasks = [t for t in plan.tasks if t.id and t.title]
        total = len(active_tasks)

        for idx, task in enumerate(active_tasks):
            await on_event({
                "type": "task_start",
                "task_id": task.id,
                "title": task.title,
                "engine": task.engine,
                "total_tasks": total,
                "current_index": idx,
            })

            task_prompt = f"""执行以下任务：

任务：{task.title}
描述：{task.description or '无额外描述'}

请使用你的工具能力完成这个任务。完成后请明确说明执行结果。"""

            try:
                result = await self._run_one_engine(
                    task_prompt, task.engine, on_event,
                    phase="execution",
                )
                await on_event({
                    "type": "task_done",
                    "task_id": task.id,
                    "success": True,
                    "usage": {
                        "input_tokens": result.get("input_tokens", 0),
                        "output_tokens": result.get("output_tokens", 0),
                    },
                })
            except Exception as e:
                await on_event({
                    "type": "task_error",
                    "task_id": task.id,
                    "error": str(e),
                })

        await on_event({"type": "phase_end", "phase": "execution"})
        return self.total_usage
