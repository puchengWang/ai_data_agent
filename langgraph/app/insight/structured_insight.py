from typing import Any, Dict, List, Optional

from app.capabilities.catalog import build_capability_catalog


def build_structured_insight(
    question: str,
    aggregation_plan: Dict[str, Any],
    aggregation_result: Dict[str, Any],
    tool_results: List[Dict[str, Any]],
    capability_catalog: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    catalog = capability_catalog or build_capability_catalog()

    aggregation_type = aggregation_plan.get("aggregation_type")
    metric = _get_metric(aggregation_plan)
    dimension = aggregation_plan.get("dimension")

    insight = {
        "main_conclusion": "",
        "evidence": [],
        "interesting_points": [],
        "limitations": [],
        "available_drilldowns": _build_available_drilldowns(
            metric=metric,
            current_aggregation_type=aggregation_type,
            current_dimension=dimension,
            catalog=catalog,
        ),
        "suggestion_context": {
            "question": question,
            "metric": metric,
            "aggregation_type": aggregation_type,
            "dimension": dimension,
            "params": _get_primary_params(aggregation_plan),
            "available_dimensions": _get_available_dimensions(metric, catalog),
        },
    }

    if aggregation_result.get("error"):
        insight["limitations"].append({
            "type": "analysis_error",
            "message": aggregation_result.get("error"),
        })
        insight["main_conclusion"] = "分析结果存在错误，当前只能提供有限洞察。"
        return insight

    if aggregation_type == "normal":
        return _build_normal_insight(insight, aggregation_plan, tool_results)

    if aggregation_type == "compare":
        return _build_compare_insight(insight, aggregation_result)

    if aggregation_type == "trend":
        return _build_trend_insight(insight, aggregation_result)

    if aggregation_type in {"group_by", "top_n", "distribution"}:
        return _build_contribution_insight(insight, aggregation_result)

    if aggregation_type == "compare_by_dimension":
        return _build_compare_by_dimension_insight(insight, aggregation_result)

    if aggregation_type == "trend_by_dimension":
        return _build_trend_by_dimension_insight(insight, aggregation_result)

    insight["limitations"].append({
        "type": "unsupported_aggregation_type",
        "aggregation_type": aggregation_type,
    })
    insight["main_conclusion"] = "当前分析类型尚未生成结构化洞察。"
    return insight


def _build_normal_insight(
    insight: Dict[str, Any],
    aggregation_plan: Dict[str, Any],
    tool_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    result = _first_successful_result(tool_results)
    value = (result.get("data") or {}).get("value") if result else None

    if value is None:
        insight["main_conclusion"] = "当前查询没有返回有效数值。"
        insight["limitations"].append({
            "type": "missing_value",
            "message": "SQL 工具没有返回可用 value。",
        })
    else:
        insight["main_conclusion"] = f"当前查询结果为 {value}。"

    insight["evidence"].append({
        "type": "scalar_value",
        "value": value,
        "task_id": result.get("task_id") if result else None,
        "params": _get_primary_params(aggregation_plan),
    })

    return insight


def _build_compare_insight(
    insight: Dict[str, Any],
    aggregation_result: Dict[str, Any],
) -> Dict[str, Any]:
    growth = _operator_data(aggregation_result, "growth_rate")

    if not growth:
        insight["main_conclusion"] = "对比分析未生成有效增长率结果。"
        insight["limitations"].append({
            "type": "missing_operator_result",
            "operator": "growth_rate",
        })
        return insight

    direction = growth.get("direction")
    change = growth.get("change")
    change_rate = growth.get("change_rate")

    insight["main_conclusion"] = _format_change_conclusion(
        direction=direction,
        change=change,
        change_rate=change_rate,
    )
    insight["evidence"].append({
        "type": "period_compare",
        "current_value": growth.get("current_value"),
        "previous_value": growth.get("previous_value"),
        "change": change,
        "change_rate": change_rate,
        "direction": direction,
    })

    if direction in {"up", "down"}:
        insight["interesting_points"].append({
            "type": "period_change",
            "direction": direction,
            "change": change,
            "change_rate": change_rate,
        })

    return insight


def _build_trend_insight(
    insight: Dict[str, Any],
    aggregation_result: Dict[str, Any],
) -> Dict[str, Any]:
    analysis = aggregation_result.get("analysis") or {}
    stats = analysis.get("summary_stats") or {}
    peak_valley = _operator_data(aggregation_result, "peak_valley") or {}
    volatility = _operator_data(aggregation_result, "volatility") or {}
    anomaly = _operator_data(aggregation_result, "basic_anomaly") or {}

    change = stats.get("change")
    start_value = stats.get("start_value")
    end_value = stats.get("end_value")

    if change is None:
        insight["main_conclusion"] = "趋势分析未生成有效起止变化。"
    elif change > 0:
        insight["main_conclusion"] = (
            f"趋势期末值 {end_value} 高于期初值 {start_value}，增加 {change}。"
        )
    elif change < 0:
        insight["main_conclusion"] = (
            f"趋势期末值 {end_value} 低于期初值 {start_value}，减少 {abs(change)}。"
        )
    else:
        insight["main_conclusion"] = (
            f"趋势期初和期末均为 {start_value}，整体持平。"
        )

    insight["evidence"].append({
        "type": "trend_summary",
        "summary_stats": stats,
    })

    if peak_valley.get("peak"):
        insight["interesting_points"].append({
            "type": "peak",
            "point": peak_valley.get("peak"),
        })

    if peak_valley.get("valley"):
        insight["interesting_points"].append({
            "type": "valley",
            "point": peak_valley.get("valley"),
        })

    if volatility:
        insight["interesting_points"].append({
            "type": "volatility",
            "volatility_level": volatility.get("volatility_level"),
            "volatility_ratio": volatility.get("volatility_ratio"),
        })

    if anomaly.get("has_anomaly"):
        insight["interesting_points"].append({
            "type": "anomaly",
            "anomalies": anomaly.get("anomalies", []),
        })

    return insight


def _build_contribution_insight(
    insight: Dict[str, Any],
    aggregation_result: Dict[str, Any],
) -> Dict[str, Any]:
    contribution = _operator_data(aggregation_result, "contribution")

    if not contribution:
        insight["main_conclusion"] = "分组分析未生成有效贡献度结果。"
        insight["limitations"].append({
            "type": "missing_operator_result",
            "operator": "contribution",
        })
        return insight

    top = contribution.get("top_contributor")
    total = contribution.get("total_value")

    if top:
        insight["main_conclusion"] = (
            f"当前分组中 {top.get('dimension_value')} 贡献最高，"
            f"数值为 {top.get('value')}，占比 {top.get('contribution_rate')}%。"
        )
        insight["interesting_points"].append({
            "type": "top_contributor",
            "top_contributor": top,
        })
    else:
        insight["main_conclusion"] = "当前分组结果为空，未发现主要贡献项。"

    insight["evidence"].append({
        "type": "contribution",
        "total_value": total,
        "rows": contribution.get("rows", []),
    })

    return insight


def _build_compare_by_dimension_insight(
    insight: Dict[str, Any],
    aggregation_result: Dict[str, Any],
) -> Dict[str, Any]:
    growth = _operator_data(aggregation_result, "growth_rate") or {}
    rows = growth.get("rows", [])

    if not rows:
        insight["main_conclusion"] = "分维度对比分析未生成有效增长结果。"
        insight["limitations"].append({
            "type": "missing_operator_rows",
            "operator": "growth_rate",
        })
        return insight

    largest_increase = max(rows, key=lambda item: item.get("change", 0))
    largest_decrease = min(rows, key=lambda item: item.get("change", 0))

    insight["main_conclusion"] = (
        f"分维度对比中，{largest_increase.get('dimension_value')} 增长最多，"
        f"增加 {largest_increase.get('change')}。"
    )

    insight["evidence"].append({
        "type": "dimension_compare",
        "rows": rows,
    })

    insight["interesting_points"].append({
        "type": "largest_increase",
        "row": largest_increase,
    })

    if largest_decrease.get("change", 0) < 0:
        insight["interesting_points"].append({
            "type": "largest_decrease",
            "row": largest_decrease,
        })

    return insight


def _build_trend_by_dimension_insight(
    insight: Dict[str, Any],
    aggregation_result: Dict[str, Any],
) -> Dict[str, Any]:
    analysis = aggregation_result.get("analysis") or {}
    series = analysis.get("series", {})
    volatility = _operator_data(aggregation_result, "volatility") or {}
    anomaly = _operator_data(aggregation_result, "basic_anomaly") or {}

    insight["main_conclusion"] = f"当前按维度趋势共覆盖 {len(series)} 个维度值。"
    insight["evidence"].append({
        "type": "dimension_trend",
        "series_count": len(series),
        "dimension": analysis.get("dimension"),
    })

    high_volatility = [
        {
            "dimension_value": dimension_value,
            "volatility": item,
        }
        for dimension_value, item in volatility.items()
        if item.get("volatility_level") == "high"
    ]

    if high_volatility:
        insight["interesting_points"].append({
            "type": "high_volatility_dimensions",
            "items": high_volatility,
        })

    anomaly_dimensions = [
        {
            "dimension_value": dimension_value,
            "anomalies": item.get("anomalies", []),
        }
        for dimension_value, item in anomaly.items()
        if item.get("has_anomaly")
    ]

    if anomaly_dimensions:
        insight["interesting_points"].append({
            "type": "anomaly_dimensions",
            "items": anomaly_dimensions,
        })

    return insight


def _build_available_drilldowns(
    metric: Optional[str],
    current_aggregation_type: Optional[str],
    current_dimension: Optional[str],
    catalog: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not metric:
        return []

    metric_capability = catalog.get("metrics", {}).get(metric)
    if not metric_capability:
        return []

    dimensions = metric_capability.get("dimensions", {})
    drilldowns = []

    if current_aggregation_type == "normal":
        drilldowns.append({
            "analysis_type": "trend",
            "metric": metric,
            "dimension": None,
            "reason": "当前指标可继续查看时间趋势。",
        })

    if current_aggregation_type in {"normal", "compare", "trend"}:
        for dimension in dimensions:
            drilldowns.append({
                "analysis_type": _dimension_drilldown_type(
                    current_aggregation_type
                ),
                "metric": metric,
                "dimension": dimension,
                "reason": f"当前指标可按 {dimension} 维度继续拆解。",
            })

    if (
        current_aggregation_type in {"group_by", "top_n", "distribution"}
        and current_dimension
    ):
        drilldowns.append({
            "analysis_type": "trend_by_dimension",
            "metric": metric,
            "dimension": current_dimension,
            "reason": f"当前分组结果可继续查看 {current_dimension} 的趋势变化。",
        })

    if current_aggregation_type == "compare_by_dimension" and current_dimension:
        drilldowns.append({
            "analysis_type": "trend_by_dimension",
            "metric": metric,
            "dimension": current_dimension,
            "reason": f"当前分维度对比结果可继续查看 {current_dimension} 的趋势。",
        })

    return [
        item for item in drilldowns
        if item["analysis_type"] in catalog.get("analysis_types", {})
    ]


def _dimension_drilldown_type(current_aggregation_type: Optional[str]) -> str:
    if current_aggregation_type == "compare":
        return "compare_by_dimension"

    if current_aggregation_type == "trend":
        return "trend_by_dimension"

    return "group_by"


def _operator_data(
    aggregation_result: Dict[str, Any],
    operator_name: str,
) -> Optional[Any]:
    result = (
        aggregation_result
        .get("operator_results", {})
        .get(operator_name)
    )

    if not result or not result.get("success"):
        return None

    return result.get("data")


def _first_successful_result(
    tool_results: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    for result in tool_results:
        if result.get("success"):
            return result

    return None


def _get_metric(aggregation_plan: Dict[str, Any]) -> Optional[str]:
    tasks = aggregation_plan.get("tasks", [])
    if not tasks:
        return None

    return tasks[0].get("metric")


def _get_primary_params(aggregation_plan: Dict[str, Any]) -> Dict[str, Any]:
    tasks = aggregation_plan.get("tasks", [])
    if not tasks:
        return {}

    return tasks[0].get("params", {}) or {}


def _get_available_dimensions(
    metric: Optional[str],
    catalog: Dict[str, Any],
) -> List[str]:
    if not metric:
        return []

    metric_capability = catalog.get("metrics", {}).get(metric, {})
    return sorted(metric_capability.get("dimensions", {}).keys())


def _format_change_conclusion(
    direction: Optional[str],
    change: Any,
    change_rate: Any,
) -> str:
    if direction == "up":
        return f"当前周期相比上一周期增加 {change}，增长率为 {change_rate}%。"

    if direction == "down":
        return f"当前周期相比上一周期减少 {abs(change)}，变化率为 {change_rate}%。"

    if direction == "flat":
        return "当前周期相比上一周期基本持平。"

    return "当前周期与上一周期的变化方向不明确。"
