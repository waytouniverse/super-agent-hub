"""多轮辩论编排器"""

import asyncio
from .base import BaseTeamOrchestrator, ENGINE_DISPLAY
from .prompts import build_engine_prompt, build_judge_prompt
from .judge import parse_judge_response


class DebateOrchestrator(BaseTeamOrchestrator):
    """多轮辩论模式：每轮所有引擎并行发言，裁判评估是否继续"""

    def __init__(self, engines: list[str], cwd: str, config: dict):
        super().__init__(engines, cwd, config)
        self.max_rounds = config.get("max_rounds", 3)
        self.judge_engine = config.get("judge_engine", "")

    async def run(self, user_prompt: str, on_event) -> list[dict]:
        await on_event({"type": "phase_start", "phase": "discussion"})

        all_round_transcripts: list[dict] = []

        for round_num in range(1, self.max_rounds + 1):
            await on_event({
                "type": "round_start",
                "round": round_num,
                "max_rounds": self.max_rounds,
            })

            # 每轮：所有引擎并行发言
            async def run_engine(eng: str):
                prompt = build_engine_prompt(
                    user_prompt, eng, 0, len(self.engines),
                    all_round_transcripts, mode="debate",
                )
                return await self._run_one_engine(
                    prompt, eng, on_event, phase="discussion", round_num=round_num,
                )

            tasks = [run_engine(e) for e in self.engines if e in ENGINE_DISPLAY]
            results = await asyncio.gather(*tasks)

            # 记录本轮发言
            round_transcripts = []
            for r in results:
                content = r.get("content", "")
                engine = r.get("engine", "")
                all_round_transcripts.append({
                    "engine": engine,
                    "content": content,
                    "round": round_num,
                })
                round_transcripts.append(
                    f"### {ENGINE_DISPLAY.get(engine, engine)}：\n{content}"
                )

            # 裁判评估（如果配置了裁判引擎）
            judge_concluded = False
            if self.judge_engine and self.judge_engine in ENGINE_DISPLAY:
                judge_prompt = build_judge_prompt(
                    round_num, self.max_rounds, round_transcripts,
                )
                judge_result = await self._run_one_engine(
                    judge_prompt, self.judge_engine, on_event,
                    phase="judge", round_num=round_num,
                )
                judge_content = judge_result.get("content", "")
                decision = parse_judge_response(judge_content)
                decision_value = decision.get("decision", "CONTINUE")
                judge_concluded = decision_value == "CONCLUDE"
                await on_event({
                    "type": "judge_decision",
                    "round": round_num,
                    "decision": decision_value,
                    "evaluation": decision.get("evaluation", ""),
                    "final_summary": decision.get("final_summary", ""),
                })
            else:
                # 无裁判：最后一轮自动结束
                is_last = round_num >= self.max_rounds
                await on_event({
                    "type": "judge_decision",
                    "round": round_num,
                    "decision": "CONCLUDE" if is_last else "CONTINUE",
                    "evaluation": f"第 {round_num}/{self.max_rounds} 轮完成（无裁判模式）",
                    "final_summary": "",
                })

            await on_event({"type": "round_end", "round": round_num})

            # 裁判判定 CONCLUDE 或达到最大轮数时停止
            if judge_concluded or round_num >= self.max_rounds:
                break

        await on_event({"type": "phase_end", "phase": "discussion"})
        return self.total_usage
