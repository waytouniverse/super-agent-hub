"""裁判 prompt 构建 + 响应解析"""

import json
import re


def parse_judge_response(raw_text: str) -> dict:
    """从引擎输出中提取裁判 JSON 判定"""
    # 尝试1：直接 JSON 解析
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # 尝试2：提取 ```json ... ``` 代码块
    m = re.search(r'```json\s*\n?(.*?)\n?```', raw_text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试3：提取最外层 { ... }
    m = re.search(r'\{[^{}]*"decision"[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw_text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    # 兜底：返回默认 CONTINUE
    return {
        "decision": "CONTINUE",
        "evaluation": raw_text[:500],
        "final_summary": "",
    }
