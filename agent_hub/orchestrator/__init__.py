"""多引擎团队编排器"""

from .base import BaseTeamOrchestrator, ADAPTER_MAP, ENGINE_DISPLAY
from .serial import SerialOrchestrator
from .parallel import ParallelOrchestrator
from .debate import DebateOrchestrator
from .consultation import ConsultationOrchestrator
from .prompts import build_engine_prompt, build_judge_prompt
from .judge import parse_judge_response
from .task_plan import TaskPlan, Plan, parse_plan_from_text


def create_orchestrator(mode: str, engines: list[str], cwd: str, config: dict):
    """工厂函数：根据模式创建对应的编排器"""
    if mode == "parallel":
        return ParallelOrchestrator(engines, cwd, config)
    elif mode == "debate":
        return DebateOrchestrator(engines, cwd, config)
    elif mode == "consultation":
        return ConsultationOrchestrator(engines, cwd, config)
    else:
        return SerialOrchestrator(engines, cwd, config)
