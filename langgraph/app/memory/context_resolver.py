from typing import Any, Dict

from app.memory.context_strategy import detect_context_strategy


RESET_CONTEXT_KEYWORDS = [
    "重新开始",
    "忽略上文",
    "不要参考之前",
    "新问题",
    "清空上下文",
    "重新分析",
]

FOLLOW_UP_KEYWORDS = [
    "哪个",
    "哪一个",
    "为什么",
    "继续",
    "再看",
    "下降最多",
    "增长最多",
    "和昨天比",
    "和上周比",
    "那",
    "这个",
    "刚才",
    "上面",
]


def is_follow_up_question(question: str) -> bool:
    if "到" in question and any(ch.isdigit() for ch in question):
        return False

    return any(keyword in question for keyword in FOLLOW_UP_KEYWORDS)


def build_inherited_context(last_context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "last_question": last_context.get("question"),
        "last_resolved_question": last_context.get("resolved_question"),
        "last_aggregation_type": last_context.get("aggregation_type"),
        "last_metric": last_context.get("metric"),
        "last_dimension": last_context.get("dimension"),
        "last_params": last_context.get("params"),
        "last_tasks": last_context.get("tasks"),
        "last_query_plans": last_context.get("query_plans"),
        "last_analysis": last_context.get("aggregation_result"),
        "last_structured_insight": last_context.get("structured_insight"),
        "last_follow_up_suggestions": last_context.get(
            "follow_up_suggestions",
            [],
        ),
        "last_answer": last_context.get("answer"),
    }


def resolve_question_with_context(
    question: str,
    last_context: Dict[str, Any],
) -> Dict[str, Any]:

    if not last_context:
        return {
            "is_follow_up": False,
            "reset_context": False,
            "context_strategy": {
                "use_context": False,
                "reset_context": False,
                "reason": "no_previous_context",
            },
            "resolved_question": question,
            "inherited_context": {},
        }

    # 兜底：用户明确要求重置时，不必调用 LLM
    if any(keyword in question for keyword in RESET_CONTEXT_KEYWORDS):
        return {
            "is_follow_up": False,
            "reset_context": True,
            "context_strategy": {
                "use_context": False,
                "reset_context": True,
                "reason": "matched_reset_keyword",
            },
            "resolved_question": question,
            "inherited_context": {},
        }

    # 主逻辑：让 LLM 判断是否继承上下文
    strategy = detect_context_strategy(
        question=question,
        last_context=last_context,
    )

    if strategy.get("reset_context"):
        return {
            "is_follow_up": False,
            "reset_context": True,
            "context_strategy": strategy,
            "resolved_question": question,
            "inherited_context": {},
        }

    if not strategy.get("use_context"):
        return {
            "is_follow_up": False,
            "reset_context": False,
            "context_strategy": strategy,
            "resolved_question": question,
            "inherited_context": {},
        }

    inherited_context = build_inherited_context(last_context)

    resolved_question = f"""
基于上一轮分析上下文：

上一轮问题：
{inherited_context.get("last_question")}

上一轮分析类型：
{inherited_context.get("last_aggregation_type")}

上一轮指标：
{inherited_context.get("last_metric")}

上一轮维度：
{inherited_context.get("last_dimension")}

上一轮参数：
{inherited_context.get("last_params")}

上一轮结构化洞察：
{inherited_context.get("last_structured_insight")}

上一轮系统建议追问：
{inherited_context.get("last_follow_up_suggestions")}

用户追问：
{question}

请结合上一轮上下文理解本轮问题。
""".strip()

    return {
        "is_follow_up": True,
        "reset_context": False,
        "context_strategy": strategy,
        "resolved_question": resolved_question,
        "inherited_context": inherited_context,
    }
