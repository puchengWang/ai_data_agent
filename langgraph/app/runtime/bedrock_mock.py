import ast
import re
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Iterator


def mock_semantic_parser_json(prompt: str) -> Dict[str, Any]:
    question = _extract_question_from_parser_prompt(prompt)
    params = _parse_time_params(question)

    if _contains_dimension(question):
        params["dimension"] = "level"

    limit = _extract_limit(question)
    if limit:
        params["limit"] = limit

    return {
        "metric": "user_count",
        "params": params,
    }


def mock_context_strategy_json(prompt: str) -> Dict[str, Any]:
    question = _extract_question_from_context_prompt(prompt)

    reset_keywords = [
        "重新开始",
        "忽略上文",
        "不要参考之前",
        "新问题",
        "清空上下文",
        "重新分析",
    ]

    if any(keyword in question for keyword in reset_keywords):
        return {
            "use_context": False,
            "reset_context": True,
            "reason": "mock_matched_reset_keyword",
        }

    if _has_complete_date(question):
        return {
            "use_context": False,
            "reset_context": False,
            "reason": "mock_complete_question",
        }

    follow_up_keywords = [
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

    if any(keyword in question for keyword in follow_up_keywords):
        return {
            "use_context": True,
            "reset_context": False,
            "reason": "mock_matched_follow_up_keyword",
        }

    return {
        "use_context": False,
        "reset_context": False,
        "reason": "mock_default_no_context",
    }


def mock_summary_text(prompt: str) -> str:
    question = _extract_label_block(
        prompt=prompt,
        label="用户问题：",
        stop_labels=[
            "查询结果：",
            "分组统计结果：",
            "趋势分析结果：",
            "TopN 分析结果：",
            "分布分析结果：",
            "聚合分析结果：",
        ],
    )

    tool_results = _extract_python_value(
        prompt=prompt,
        label="查询结果：",
        stop_labels=[
            "聚合分析结果：",
            "请直接输出最终中文回答。",
        ],
    )

    value = _first_scalar_value(tool_results)
    if value is not None:
        return f"{question} 的查询结果为 {value}。"

    aggregation_result = _extract_python_value(
        prompt=prompt,
        label="聚合分析结果：",
        stop_labels=["请直接输出最终中文回答。"],
    )

    if isinstance(aggregation_result, dict):
        conclusion = _summarize_aggregation_result(aggregation_result)
        if conclusion:
            return conclusion

    return (
        "Mock Bedrock summary: 真实 Bedrock 当前不可用，本次仅用于验证 "
        "Planner 之后的分析闭环。"
    )


@contextmanager
def mock_bedrock_calls(
    graph_module,
    context_strategy_module,
) -> Iterator[None]:
    original_graph_json = graph_module.invoke_bedrock_json
    original_graph_text = graph_module.invoke_bedrock_text
    original_context_json = context_strategy_module.invoke_bedrock_json

    graph_module.invoke_bedrock_json = mock_semantic_parser_json
    graph_module.invoke_bedrock_text = mock_summary_text
    context_strategy_module.invoke_bedrock_json = mock_context_strategy_json

    try:
        yield
    finally:
        graph_module.invoke_bedrock_json = original_graph_json
        graph_module.invoke_bedrock_text = original_graph_text
        context_strategy_module.invoke_bedrock_json = original_context_json


def _extract_question_from_parser_prompt(prompt: str) -> str:
    match = re.search(r"用户问题：\s*(.*?)\s*输出格式：", prompt, re.S)
    if match:
        return match.group(1).strip()

    return prompt


def _extract_question_from_context_prompt(prompt: str) -> str:
    match = re.search(r"当前用户问题：\s*(.*?)\s*判断规则：", prompt, re.S)
    if match:
        return match.group(1).strip()

    return prompt


def _parse_time_params(question: str) -> Dict[str, Any]:
    date_matches = re.findall(r"\d{4}-\d{2}-\d{2}", question)

    if len(date_matches) >= 2:
        start_dt = datetime.strptime(date_matches[0], "%Y-%m-%d")
        end_dt = datetime.strptime(date_matches[1], "%Y-%m-%d") + timedelta(days=1)
        return {
            "start_time": start_dt.strftime("%Y-%m-%d"),
            "end_time": end_dt.strftime("%Y-%m-%d"),
            "grain": "day",
        }

    if len(date_matches) == 1:
        start_dt = datetime.strptime(date_matches[0], "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=1)
        return {
            "start_time": start_dt.strftime("%Y-%m-%d"),
            "end_time": end_dt.strftime("%Y-%m-%d"),
            "grain": "day",
        }

    raise ValueError(
        "Mock Bedrock parser requires at least one YYYY-MM-DD date in the question."
    )


def _contains_dimension(question: str) -> bool:
    dimension_keywords = [
        "level",
        "等级",
        "用户等级",
        "各",
        "按",
        "分布",
    ]
    return any(keyword in question for keyword in dimension_keywords)


def _extract_limit(question: str) -> int | None:
    match = re.search(r"前\s*(\d+)", question)
    if match:
        return int(match.group(1))

    match = re.search(r"top\s*(\d+)", question.lower())
    if match:
        return int(match.group(1))

    return None


def _has_complete_date(question: str) -> bool:
    return bool(re.findall(r"\d{4}-\d{2}-\d{2}", question))


def _extract_label_block(
    prompt: str,
    label: str,
    stop_labels: list[str],
) -> str:
    start = prompt.find(label)
    if start < 0:
        return ""

    start += len(label)
    end = len(prompt)

    for stop_label in stop_labels:
        stop = prompt.find(stop_label, start)
        if stop >= 0:
            end = min(end, stop)

    return prompt[start:end].strip()


def _extract_python_value(
    prompt: str,
    label: str,
    stop_labels: list[str],
) -> Any:
    text = _extract_label_block(prompt, label, stop_labels)
    if not text:
        return None

    try:
        return ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return None


def _first_scalar_value(value: Any) -> Any:
    if not isinstance(value, list):
        return None

    for item in value:
        if not isinstance(item, dict):
            continue

        data = item.get("data") or {}
        if "value" in data:
            return data["value"]

    return None


def _summarize_aggregation_result(aggregation_result: Dict[str, Any]) -> str | None:
    aggregation_type = aggregation_result.get("aggregation_type")
    analysis = aggregation_result.get("analysis") or {}

    if aggregation_type == "normal":
        value = _first_scalar_value(analysis.get("tool_results") or [])
        if value is not None:
            return f"当前查询结果为 {value}。"

    operator_results = aggregation_result.get("operator_results") or {}

    growth_rate = operator_results.get("growth_rate") or {}
    if growth_rate.get("success") and isinstance(growth_rate.get("data"), dict):
        data = growth_rate["data"]
        if "change" in data:
            return (
                f"当前值为 {data.get('current_value')}，"
                f"对比值为 {data.get('previous_value')}，"
                f"变化值为 {data.get('change')}，"
                f"变化率为 {data.get('change_rate')}%。"
            )

    contribution = operator_results.get("contribution") or {}
    if contribution.get("success") and isinstance(contribution.get("data"), dict):
        top = contribution["data"].get("top_contributor")
        if top:
            return (
                f"当前分组中 {top.get('dimension_value')} 数值最高，"
                f"为 {top.get('value')}，占比 {top.get('contribution_rate')}%。"
            )

    return None
