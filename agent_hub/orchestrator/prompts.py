"""团队模式 prompt 构建"""

import re

TEAM_RUNTIME_NOTES = [
    "你是一个 AI 团队中的成员，正在参与多引擎协作讨论。",
    "请用中文回复。",
    "不要使用 Read 工具读取图片、视频、PDF 等二进制文件。",
    "",
]

ENGINE_DISPLAY = {
    "claude": "Claude",
    "codex": "Codex",
    "hermes": "Hermes",
}


def build_engine_prompt(
    user_prompt: str,
    engine_name: str,
    engine_index: int,
    total_engines: int,
    previous_responses: list[dict],
    mode: str = "serial",
) -> str:
    """为每个引擎构建带上下文的 prompt"""
    lines = TEAM_RUNTIME_NOTES.copy()
    display = ENGINE_DISPLAY.get(engine_name, engine_name)

    if mode == "parallel":
        lines.extend([
            f"你是团队中的**{display}**引擎。请针对用户的问题给出你的独立分析和回答。",
            "其他引擎也在同时回答，你们各自独立工作，不需要审查他人。",
            "",
            f"用户问题：{user_prompt}",
        ])
        return "\n".join(lines)

    if mode == "debate":
        if not previous_responses:
            lines.extend([
                f"你是团队中的**{display}**引擎。这是第 1 轮讨论。请针对用户问题给出你的独立分析。",
                "",
                f"用户问题：{user_prompt}",
            ])
        else:
            lines.extend([
                f"你是团队中的**{display}**引擎。这是新一轮讨论。以下是你前面所有轮次的讨论记录：",
                "",
            ])
            for i, resp in enumerate(previous_responses):
                prev_display = ENGINE_DISPLAY.get(resp["engine"], resp["engine"])
                content = resp["content"]
                if len(content) > 3000:
                    content = content[:3000] + "\n...[内容已截断]"
                lines.append(f"### 第{resp.get('round', '?')}轮 — {prev_display}：")
                lines.append(content)
                lines.append("")
            lines.extend([
                f"用户原始问题：{user_prompt}",
                "",
                "请基于前面的讨论，给出你新一轮的观点。可以反驳、补充、或提出新的角度。",
                "不要简单重复之前已经说过的内容。",
            ])
        return "\n".join(lines)

    # serial mode (默认)
    if engine_index == 0:
        lines.extend([
            f"你是团队中的**首位发言人**（{display}）。请直接、全面地回答用户的问题。",
            "",
            f"用户问题：{user_prompt}",
        ])
    elif engine_index == total_engines - 1:
        lines.extend([
            f"你是团队中的**最终审查者和总结者**（{display}）。以下是你前面同事的全部发言：",
            "",
        ])
        for i, resp in enumerate(previous_responses):
            prev_display = ENGINE_DISPLAY.get(resp["engine"], resp["engine"])
            content = resp["content"]
            if len(content) > 3000:
                content = content[:3000] + "\n...[内容已截断]"
            lines.append(f"### {prev_display} 的发言：")
            lines.append(content)
            lines.append("")
        lines.extend([
            f"用户原始问题：{user_prompt}",
            "",
            "请综合以上所有发言，指出各方的亮点和不足，给出一个完整的最终答案。",
            "如果前面有错误，请纠正；如果有遗漏，请补充。",
        ])
    else:
        lines.extend([
            f"你是团队中的**审查者**（{display}）。以下是你前面同事的发言：",
            "",
        ])
        for i, resp in enumerate(previous_responses):
            prev_display = ENGINE_DISPLAY.get(resp["engine"], resp["engine"])
            content = resp["content"]
            if len(content) > 3000:
                content = content[:3000] + "\n...[内容已截断]"
            lines.append(f"### {prev_display} 的发言：")
            lines.append(content)
            lines.append("")
        lines.extend([
            f"用户原始问题：{user_prompt}",
            "",
            "请审查以上发言：指出逻辑漏洞、事实错误或遗漏点，并补充你自己的见解。",
            "不要简单重复前面已经说过的内容——聚焦于他们没讲到的部分。",
        ])

    return "\n".join(lines)


def build_judge_prompt(
    round_num: int,
    max_rounds: int,
    round_transcripts: list[str],
) -> str:
    """构建裁判评估 prompt"""
    lines = [
        "你是 AI 团队中的**裁判**。你的职责是评估本轮讨论的质量，判断是否需要继续。",
        "",
        f"这是第 {round_num} 轮讨论（最多 {max_rounds} 轮）。以下是本轮所有引擎的发言：",
        "",
    ]
    for ts in round_transcripts:
        lines.append(ts)
        lines.append("")

    lines.extend([
        "请按以下 JSON 格式回复：",
        "```json",
        "{",
        '  "decision": "CONTINUE 或 CONCLUDE",',
        '  "evaluation": "对本轮讨论的分析（共识点、分歧点、遗漏点）",',
        '  "final_summary": "如果 CONCLUDE，给出综合结论；如果 CONTINUE，说明还需要讨论什么"',
        "}",
        "```",
        "",
        "判断标准：",
        "- 如果各方观点已经充分表达，分歧已明确，或已有明显共识 → CONCLUDE",
        "- 如果仍有重要角度未讨论到，或存在明显误解需要澄清 → CONTINUE",
        f"- 这是第 {round_num}/{max_rounds} 轮，如果已经到了最后一轮，请务必 CONCLUDE",
    ])
    return "\n".join(lines)


def extract_clean_content(text: str) -> str:
    """去掉系统提示等噪音，提取核心回复内容"""
    text = re.sub(r'Agent Hub 运行约束：.*?\n\n', '', text, flags=re.DOTALL)
    return text.strip()
