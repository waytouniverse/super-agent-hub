"""多引擎团队编排器 — 兼容导入（使用 orchestrator/ 子包）"""

from .orchestrator.base import ADAPTER_MAP, ENGINE_DISPLAY, BaseTeamOrchestrator
from .orchestrator.serial import SerialOrchestrator
from .orchestrator.parallel import ParallelOrchestrator
from .orchestrator.debate import DebateOrchestrator
from .orchestrator.consultation import ConsultationOrchestrator
from .orchestrator.prompts import build_engine_prompt, build_judge_prompt
from .orchestrator import create_orchestrator

# 向后兼容：TeamOrchestrator 别名 → SerialOrchestrator
TeamOrchestrator = SerialOrchestrator
