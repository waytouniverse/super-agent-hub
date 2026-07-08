"""串行审查编排器"""

from .base import BaseTeamOrchestrator, ENGINE_DISPLAY
from .prompts import build_engine_prompt


class SerialOrchestrator(BaseTeamOrchestrator):
    """串行审查模式：引擎依次发言，后者看到前者的输出"""

    async def run(self, user_prompt: str, on_event) -> list[dict]:
        await on_event({"type": "phase_start", "phase": "discussion"})

        previous_responses: list[dict] = []

        for idx, engine_name in enumerate(self.engines):
            if engine_name not in ENGINE_DISPLAY:
                await on_event({
                    "type": "error",
                    "engine": engine_name,
                    "content": f"不支持的引擎: {engine_name}",
                })
                continue

            engine_prompt = build_engine_prompt(
                user_prompt, engine_name, idx, len(self.engines),
                previous_responses, mode="serial",
            )

            result = await self._run_one_engine(
                engine_prompt, engine_name, on_event, phase="discussion",
            )

            previous_responses.append({
                "engine": engine_name,
                "content": result.get("content", ""),
            })

        await on_event({"type": "phase_end", "phase": "discussion"})
        return self.total_usage
