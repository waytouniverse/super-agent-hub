"""并行讨论编排器"""

import asyncio
from .base import BaseTeamOrchestrator, ENGINE_DISPLAY
from .prompts import build_engine_prompt


class ParallelOrchestrator(BaseTeamOrchestrator):
    """并行讨论模式：所有引擎同时回答同一 prompt"""

    async def run(self, user_prompt: str, on_event) -> list[dict]:
        await on_event({"type": "phase_start", "phase": "discussion"})

        async def run_engine(engine_name: str) -> dict:
            prompt = build_engine_prompt(
                user_prompt, engine_name, 0, len(self.engines),
                [], mode="parallel",
            )
            return await self._run_one_engine(
                prompt, engine_name, on_event, phase="discussion",
            )

        tasks = [run_engine(e) for e in self.engines if e in ENGINE_DISPLAY]
        await asyncio.gather(*tasks)

        await on_event({"type": "phase_end", "phase": "discussion"})
        return self.total_usage
