"""任务计划数据类"""

from dataclasses import dataclass, field


@dataclass
class TaskPlan:
    id: str
    title: str
    description: str = ""
    engine: str = "claude"
    estimated_tool_calls: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "engine": self.engine,
            "estimated_tool_calls": self.estimated_tool_calls,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskPlan":
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            engine=d.get("engine", "claude"),
            estimated_tool_calls=d.get("estimated_tool_calls", []),
        )


@dataclass
class Plan:
    summary: str = ""
    tasks: list[TaskPlan] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Plan":
        return cls(
            summary=d.get("summary", ""),
            tasks=[TaskPlan.from_dict(t) for t in d.get("tasks", [])],
        )


def parse_plan_from_text(text: str) -> Plan:
    """从引擎输出中解析行动计划"""
    import json
    import re

    # 尝试直接 JSON 解析
    try:
        data = json.loads(text)
        if "tasks" in data:
            return Plan.from_dict(data)
        if isinstance(data, list):
            return Plan(tasks=[TaskPlan.from_dict(t) for t in data])
    except json.JSONDecodeError:
        pass

    # 尝试 ```json ... ``` 代码块
    m = re.search(r'```json\s*\n?(.*?)\n?```', text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            return Plan.from_dict(data)
        except json.JSONDecodeError:
            pass

    # 兜底：返回空计划
    return Plan(summary=text[:500], tasks=[])
