from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.semantic.semantic_engine import resolve_metric
from app.semantic.dimension_resolver import resolve_dimension_from_question

import re


def extract_limit(question: str, default: int = 10) -> int:
    match = re.search(r"前\s*(\d+)", question)
    if match:
        return int(match.group(1))

    match = re.search(r"top\s*(\d+)", question.lower())
    if match:
        return int(match.group(1))

    return default

def detect_aggregation_type(question: str) -> str:
    question = question.lower()

    trend_keywords = [
        "趋势",
        "最近",
        "近",
        "连续",
        "变化情况",
        "走势"
    ]

    compare_keywords = [
        "相比",
        "对比",
        "增长",
        "下降",
        "环比",
        "同比"
    ]

    top_n_keywords = [
        "top",
        "topn",
        "前",
        "最多",
        "最高",
        "排名",
        "排行"
    ]

    distribution_keywords = ["分布", "占比", "比例", "构成"]

    group_by_keywords = [
        "按",
        "分组",
        "分别",
        "各",
        "分布"
    ]

    has_compare = any(k in question for k in compare_keywords)
    has_dimension = any(k in question for k in group_by_keywords)

    if has_compare and has_dimension:
        return "compare_by_dimension"

    has_trend = any(k in question for k in trend_keywords)
    has_dimension = any(k in question for k in group_by_keywords)
    
    if has_trend and has_dimension:
        return "trend_by_dimension"

    for keyword in trend_keywords:
        if keyword in question:
            return "trend"

    for keyword in compare_keywords:
        if keyword in question:
            return "compare"

    for keyword in top_n_keywords:
        if keyword in question:
            return "top_n"

    for keyword in distribution_keywords:
        if keyword in question:
            return "distribution"

    for keyword in group_by_keywords:
        if keyword in question:
            return "group_by"
    
    return "normal"



def build_trend_by_dimension_tasks(
    metric: str,
    start_time: str,
    end_time: str,
    dimension: str,
    grain: str = "day",
) -> list[dict]:

    if grain != "day":
        raise ValueError(f"Unsupported trend grain: {grain}")

    start_dt = datetime.strptime(start_time, "%Y-%m-%d")
    end_dt = datetime.strptime(end_time, "%Y-%m-%d")

    tasks = []
    current_dt = start_dt
    index = 1

    while current_dt < end_dt:
        next_dt = current_dt + timedelta(days=1)

        tasks.append({
            "task_id": f"trend_dimension_{index:03d}",
            "task_name": f"{current_dt.strftime('%Y-%m-%d')} 按{dimension}趋势统计",
            "metric": metric,
            "params": {
                "start_time": current_dt.strftime("%Y-%m-%d"),
                "end_time": next_dt.strftime("%Y-%m-%d"),
                "dimension": dimension,
                "time_label": current_dt.strftime("%Y-%m-%d"),
            },
            "dimension": dimension,
        })

        current_dt = next_dt
        index += 1

    return tasks


def build_compare_by_dimension_tasks(
    metric: str,
    current_start: str,
    current_end: str,
    dimension: str,
) -> list[dict]:

    current_start_dt = datetime.strptime(current_start, "%Y-%m-%d")
    current_end_dt = datetime.strptime(current_end, "%Y-%m-%d")

    delta = current_end_dt - current_start_dt

    previous_start_dt = current_start_dt - delta
    previous_end_dt = current_start_dt

    return [
        {
            "task_id": "current_dimension_period",
            "task_name": f"当前周期按{dimension}统计",
            "metric": metric,
            "params": {
                "start_time": current_start_dt.strftime("%Y-%m-%d"),
                "end_time": current_end_dt.strftime("%Y-%m-%d"),
                "dimension": dimension,
            },
            "dimension": dimension,
        },
        {
            "task_id": "previous_dimension_period",
            "task_name": f"对比周期按{dimension}统计",
            "metric": metric,
            "params": {
                "start_time": previous_start_dt.strftime("%Y-%m-%d"),
                "end_time": previous_end_dt.strftime("%Y-%m-%d"),
                "dimension": dimension,
            },
            "dimension": dimension,
        }
    ]



def build_compare_tasks(
    metric: str,
    current_start: str,
    current_end: str
) -> List[Dict[str, Any]]:
    current_start_dt = datetime.strptime(current_start, "%Y-%m-%d")
    current_end_dt = datetime.strptime(current_end, "%Y-%m-%d")

    delta = current_end_dt - current_start_dt

    previous_start_dt = current_start_dt - delta
    previous_end_dt = current_start_dt

    return [
        {
            "task_id": "current_period",
            "task_name": "当前周期",
            "metric": metric,
            "params": {
                "start_time": current_start_dt.strftime("%Y-%m-%d"),
                "end_time": current_end_dt.strftime("%Y-%m-%d"),
            }
        },
        {
            "task_id": "previous_period",
            "task_name": "对比周期",
            "metric": metric,
            "params": {
                "start_time": previous_start_dt.strftime("%Y-%m-%d"),
                "end_time": previous_end_dt.strftime("%Y-%m-%d"),
            }
        }
    ]


def build_trend_tasks(
    metric: str,
    start_time: str,
    end_time: str,
    grain: str = "day"
) -> List[Dict[str, Any]]:
    if grain != "day":
        raise ValueError(f"Unsupported trend grain: {grain}")

    start_dt = datetime.strptime(start_time, "%Y-%m-%d")
    end_dt = datetime.strptime(end_time, "%Y-%m-%d")

    tasks = []
    current_dt = start_dt
    index = 1

    while current_dt < end_dt:
        next_dt = current_dt + timedelta(days=1)

        tasks.append({
            "task_id": f"trend_{index:03d}",
            "task_name": f"{current_dt.strftime('%Y-%m-%d')} 指标值",
            "metric": metric,
            "params": {
                "start_time": current_dt.strftime("%Y-%m-%d"),
                "end_time": next_dt.strftime("%Y-%m-%d"),
                "time_label": current_dt.strftime("%Y-%m-%d"),
            }
        })

        current_dt = next_dt
        index += 1

    return tasks


def build_aggregation_plan(parsed_question: Dict[str, Any]) -> Dict[str, Any]:
    question = parsed_question.get("original_question") or parsed_question["question"]
#    question = parsed_question["question"]

    metric = parsed_question["metric"]
    params = parsed_question["params"]

    print("parsed_question =", parsed_question)
    aggregation_type = detect_aggregation_type(question)

    print("detected aggregation_type =", aggregation_type)
    
    if aggregation_type == "normal":
        return {
            "aggregation_type": "normal",
            "tasks": [
                {
                    "task_id": "single_task",
                    "task_name": "普通查询",
                    "metric": metric,
                    "params": params
                }
            ]
        }

    if aggregation_type == "compare_by_dimension":
        metric_def = resolve_metric(metric)
    
        dimension = (
            params.get("dimension")
            or resolve_dimension_from_question(question, metric_def)
        )
    
        if not dimension:
            raise ValueError("compare_by_dimension query requires dimension")
    
        tasks = build_compare_by_dimension_tasks(
            metric=metric,
            current_start=params["start_time"],
            current_end=params["end_time"],
            dimension=dimension,
        )
    
        return {
            "aggregation_type": "compare_by_dimension",
            "compare_mode": "period_over_period",
            "dimension": dimension,
            "tasks": tasks,
        }

    if aggregation_type == "compare":
        tasks = build_compare_tasks(
            metric=metric,
            current_start=params["start_time"],
            current_end=params["end_time"]
        )

        return {
            "aggregation_type": "compare",
            "compare_mode": "period_over_period",
            "tasks": tasks
        }
    
    if aggregation_type == "trend_by_dimension":
        metric_def = resolve_metric(metric)
    
        dimension = (
            params.get("dimension")
            or resolve_dimension_from_question(question, metric_def)
        )
    
        if not dimension:
            raise ValueError("trend_by_dimension query requires dimension")
    
        tasks = build_trend_by_dimension_tasks(
            metric=metric,
            start_time=params["start_time"],
            end_time=params["end_time"],
            dimension=dimension,
            grain=params.get("grain", "day"),
        )
    
        return {
            "aggregation_type": "trend_by_dimension",
            "dimension": dimension,
            "grain": params.get("grain", "day"),
            "tasks": tasks,
        }

    if aggregation_type == "trend":
        tasks = build_trend_tasks(
            metric=metric,
            start_time=params["start_time"],
            end_time=params["end_time"],
            grain=params.get("grain", "day")
        )

        return {
            "aggregation_type": "trend",
            "grain": params.get("grain", "day"),
            "tasks": tasks
        }

    if aggregation_type == "group_by":
        metric_def = resolve_metric(metric)
    
        dimension = (
            params.get("dimension")
            or resolve_dimension_from_question(question, metric_def)
        )
    
        if not dimension:
            raise ValueError("group_by query requires dimension")
    
        return {
            "aggregation_type": "group_by",
            "dimension": dimension,
            "tasks": [
                {
                    "task_id": "group_by_001",
                    "task_name": f"按{dimension}分组统计",
                    "metric": metric,
                    "params": {
                        **params,
                        "dimension": dimension,
                    },
                    "dimension": dimension,
                }
            ]
        }
    

    if aggregation_type == "top_n":
        metric_def = resolve_metric(metric)
    
        dimension = (
            params.get("dimension")
            or resolve_dimension_from_question(question, metric_def)
        )
    
        if not dimension:
            raise ValueError("top_n query requires dimension")
    
        limit = params.get("limit") or extract_limit(question, default=10)
    
        return {
            "aggregation_type": "top_n",
            "dimension": dimension,
            "limit": limit,
            "order": "desc",
            "tasks": [
                {
                    "task_id": "top_n_001",
                    "task_name": f"按{dimension}统计 Top {limit}",
                    "metric": metric,
                    "params": {
                        **params,
                        "dimension": dimension,
                        "limit": limit,
                        "order": "desc",
                    },
                    "dimension": dimension,
                    "limit": limit,
                    "order": "desc",
                }
            ]
        }
    

    if aggregation_type == "distribution":
        metric_def = resolve_metric(metric)
    
        dimension = (
            params.get("dimension")
            or resolve_dimension_from_question(question, metric_def)
        )
    
        if not dimension:
            raise ValueError("distribution query requires dimension")
    
        return {
            "aggregation_type": "distribution",
            "dimension": dimension,
            "tasks": [
                {
                    "task_id": "distribution_001",
                    "task_name": f"按{dimension}统计分布",
                    "metric": metric,
                    "params": {
                        **params,
                        "dimension": dimension,
                    },
                    "dimension": dimension,
                }
            ]
        }

    return {
        "aggregation_type": "unknown",
        "tasks": []
    }