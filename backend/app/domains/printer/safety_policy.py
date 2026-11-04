"""诊断与回答安全策略。

L1 低风险：观察灯态、确认纸张规格、检查外部连接、普通设置。
L2 谨慎操作：清除可见卡纸、按说明清洁可维护部件（需展示官方安全要求）。
L3 高风险：拆机、电源组件、电路板、内部电气维修 —— 禁止自助指导。
"""

from __future__ import annotations

RISK_LEVELS = {
    "L1": "低风险",
    "L2": "谨慎操作",
    "L3": "高风险",
}

# 用户明确要求自助拆修的表述
HIGH_RISK_KEYWORDS = (
    "拆机",
    "拆开",
    "拆解",
    "拆下外壳",
    "打开外壳",
    "电源板",
    "电源组件",
    "电路板",
    "主板",
    "高压",
    "内部电路",
    "内部电气",
    "自己修电路",
    "改装电路",
    "短接",
    "强行短接",
)

CAUTION_KEYWORDS = ("清洁", "滚轮", "卡纸", "喷头", "墨头", "擦拭", "取出纸张", "校准")

SAFETY_NOTICE = (
    "涉及拆机、电源组件、电路板或内部电气维修的操作属于高风险，平台不提供自助拆修步骤，"
    "请停止操作并联系专业售后。"
)

EVIDENCE_INSUFFICIENT_NOTICE = (
    "当前知识库中没有足够且适用于该型号的已审核证据来支持进一步操作，"
    "建议补充故障现象、错误码或灯态，或提交售后工单转人工处理。"
)


def classify_text_risk(text: str | None) -> str:
    """估计用户描述/请求涉及的风险等级。"""
    if not text:
        return "L1"
    lowered = text.lower()
    if any(keyword in lowered for keyword in HIGH_RISK_KEYWORDS):
        return "L3"
    if any(keyword in lowered for keyword in CAUTION_KEYWORDS):
        return "L2"
    return "L1"


def is_high_risk_request(text: str | None) -> bool:
    return classify_text_risk(text) == "L3"


def step_risk(step: dict) -> str:
    level = (step or {}).get("risk_level") or "L1"
    return level if level in RISK_LEVELS else "L1"


def filter_self_service_steps(steps: list[dict]) -> list[dict]:
    """只保留允许用户自助执行的步骤（L1/L2）。"""
    return [step for step in steps if step_risk(step) != "L3"]


def allows_step(step: dict, requested_risk: str = "L1") -> bool:
    """L3 永远不进入用户自助流程；用户明确要求 L3 时也不再继续生成步骤。"""
    if requested_risk == "L3":
        return False
    return step_risk(step) != "L3"


def refusal_answer() -> str:
    return (
        f"{SAFETY_NOTICE}\n\n"
        "我可以帮助你确认故障现象、查询官方维护说明或创建售后工单；"
        "请不要自行拆开设备外壳或接触电源、电路板部件。"
    )


def risk_label(level: str | None) -> str:
    return RISK_LEVELS.get(level or "L1", "低风险")
