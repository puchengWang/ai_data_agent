from typing import Any, Dict, List, Optional

from app.capabilities.catalog import (
    build_capability_catalog,
    validate_capability,
)


MAX_SUGGESTIONS = 4


def generate_follow_up_suggestions(
    structured_insight: Dict[str, Any],
    capability_catalog: Optional[Dict[str, Any]] = None,
    max_suggestions: int = MAX_SUGGESTIONS,
) -> List[Dict[str, Any]]:
    catalog = capability_catalog or build_capability_catalog()

    context = structured_insight.get("suggestion_context", {})
    aggregation_type = context.get("aggregation_type")
    metric = context.get("metric")
    dimension = context.get("dimension")
    params = context.get("params", {}) or {}

    candidates = []

    if aggregation_type == "normal":
        candidates.extend(_normal_suggestions(
            metric=metric,
            params=params,
            structured_insight=structured_insight,
        ))

    elif aggregation_type == "compare":
        candidates.extend(_compare_suggestions(
            metric=metric,
            params=params,
            structured_insight=structured_insight,
        ))

    elif aggregation_type == "trend":
        candidates.extend(_trend_suggestions(
            metric=metric,
            params=params,
            structured_insight=structured_insight,
        ))

    elif aggregation_type in {"group_by", "top_n", "distribution"}:
        candidates.extend(_dimension_summary_suggestions(
            metric=metric,
            dimension=dimension,
            params=params,
        ))

    elif aggregation_type == "compare_by_dimension":
        candidates.extend(_compare_by_dimension_suggestions(
            metric=metric,
            dimension=dimension,
            params=params,
        ))

    elif aggregation_type == "trend_by_dimension":
        candidates.extend(_trend_by_dimension_suggestions(
            metric=metric,
            dimension=dimension,
            params=params,
            structured_insight=structured_insight,
        ))

    valid_suggestions = [
        suggestion
        for suggestion in candidates
        if _is_valid_suggestion(suggestion, catalog)
    ]

    return _deduplicate_suggestions(valid_suggestions)[:max_suggestions]


def _normal_suggestions(
    metric: Optional[str],
    params: Dict[str, Any],
    structured_insight: Dict[str, Any],
) -> List[Dict[str, Any]]:
    suggestions = []

    if metric:
        suggestions.append(_build_suggestion(
            question="查看这段时间每天新增用户数量的趋势",
            reason="当前只回答了单点数值，可以继续查看时间趋势判断是否稳定。",
            expected_analysis_type="trend",
            metric=metric,
            dimension=None,
            params=params,
            source="normal_to_trend",
        ))

    for drilldown in structured_insight.get("available_drilldowns", []):
        if drilldown.get("analysis_type") == "group_by":
            dimension = drilldown.get("dimension")
            suggestions.append(_build_suggestion(
                question="按用户等级拆解新增用户数量",
                reason=(
                    drilldown.get("reason")
                    or "当前指标可以按可用维度继续拆解。"
                ),
                expected_analysis_type="group_by",
                metric=metric,
                dimension=dimension,
                params=params,
                source="normal_to_group_by",
            ))

    return suggestions


def _compare_suggestions(
    metric: Optional[str],
    params: Dict[str, Any],
    structured_insight: Dict[str, Any],
) -> List[Dict[str, Any]]:
    suggestions = []

    for drilldown in structured_insight.get("available_drilldowns", []):
        if drilldown.get("analysis_type") == "compare_by_dimension":
            dimension = drilldown.get("dimension")
            suggestions.append(_build_suggestion(
                question="按用户等级看，新增用户增长主要来自哪个等级？",
                reason="当前整体发生变化，可以用可用维度拆解变化来源。",
                expected_analysis_type="compare_by_dimension",
                metric=metric,
                dimension=dimension,
                params=params,
                source="compare_to_compare_by_dimension",
            ))

    suggestions.append(_build_suggestion(
        question="查看最近一段时间每天新增用户数量的趋势",
        reason="当前对比只覆盖两个周期，可以继续查看趋势确认变化是否持续。",
        expected_analysis_type="trend",
        metric=metric,
        dimension=None,
        params=params,
        source="compare_to_trend",
    ))

    return suggestions


def _trend_suggestions(
    metric: Optional[str],
    params: Dict[str, Any],
    structured_insight: Dict[str, Any],
) -> List[Dict[str, Any]]:
    suggestions = []

    trend_dimension_drilldown = _first_drilldown(
        structured_insight=structured_insight,
        analysis_type="trend_by_dimension",
    )

    if trend_dimension_drilldown:
        for point in structured_insight.get("interesting_points", []):
            if point.get("type") in {"peak", "valley", "anomaly"}:
                suggestions.append(_build_suggestion(
                    question="按用户等级拆解趋势中的异常日期",
                    reason=(
                        "当前趋势中存在峰值、低谷或异常点，"
                        "可以用可用维度继续拆解。"
                    ),
                    expected_analysis_type="trend_by_dimension",
                    metric=metric,
                    dimension=trend_dimension_drilldown.get("dimension"),
                    params=params,
                    source=f"trend_{point.get('type')}_to_dimension",
                ))
                break

        suggestions.append(_build_suggestion(
            question="按用户等级查看新增用户趋势",
            reason=(
                trend_dimension_drilldown.get("reason")
                or "当前趋势可以按可用维度继续拆解。"
            ),
            expected_analysis_type="trend_by_dimension",
            metric=metric,
            dimension=trend_dimension_drilldown.get("dimension"),
            params=params,
            source="trend_to_trend_by_dimension",
        ))

    return suggestions


def _dimension_summary_suggestions(
    metric: Optional[str],
    dimension: Optional[str],
    params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not dimension:
        return []

    return [
        _build_suggestion(
            question="查看各用户等级新增用户数量的趋势",
            reason="当前已经看到分组结构，可以继续查看各分组随时间是否稳定。",
            expected_analysis_type="trend_by_dimension",
            metric=metric,
            dimension=dimension,
            params=params,
            source="dimension_summary_to_trend_by_dimension",
        ),
        _build_suggestion(
            question="比较各用户等级新增用户数量相比前一周期的变化",
            reason="当前分组结果可以进一步对比前一周期，判断结构是否发生变化。",
            expected_analysis_type="compare_by_dimension",
            metric=metric,
            dimension=dimension,
            params=params,
            source="dimension_summary_to_compare_by_dimension",
        ),
    ]


def _compare_by_dimension_suggestions(
    metric: Optional[str],
    dimension: Optional[str],
    params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not dimension:
        return []

    return [
        _build_suggestion(
            question="查看各用户等级新增用户数量的趋势",
            reason="当前已经发现分维度变化，可以继续查看这些变化是否持续。",
            expected_analysis_type="trend_by_dimension",
            metric=metric,
            dimension=dimension,
            params=params,
            source="compare_by_dimension_to_trend_by_dimension",
        )
    ]


def _trend_by_dimension_suggestions(
    metric: Optional[str],
    dimension: Optional[str],
    params: Dict[str, Any],
    structured_insight: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not dimension:
        return []

    suggestions = []

    for point in structured_insight.get("interesting_points", []):
        if point.get("type") in {
            "high_volatility_dimensions",
            "anomaly_dimensions",
        }:
            suggestions.append(_build_suggestion(
                question="比较各用户等级新增用户数量相比前一周期的变化",
                reason="当前分维度趋势中存在波动或异常，可以继续做周期对比。",
                expected_analysis_type="compare_by_dimension",
                metric=metric,
                dimension=dimension,
                params=params,
                source="trend_by_dimension_to_compare_by_dimension",
            ))
            break

    return suggestions


def _build_suggestion(
    question: str,
    reason: str,
    expected_analysis_type: str,
    metric: Optional[str],
    dimension: Optional[str],
    params: Dict[str, Any],
    source: str,
) -> Dict[str, Any]:
    return {
        "question": question,
        "reason": reason,
        "expected_analysis_type": expected_analysis_type,
        "required_capability": {
            "metric": metric,
            "dimension": dimension,
        },
        "params_hint": params,
        "source": source,
    }


def _is_valid_suggestion(
    suggestion: Dict[str, Any],
    catalog: Dict[str, Any],
) -> bool:
    required = suggestion.get("required_capability", {})

    result = validate_capability(
        metric=required.get("metric"),
        analysis_type=suggestion.get("expected_analysis_type"),
        dimension=required.get("dimension"),
        catalog=catalog,
    )

    return result["valid"]


def _deduplicate_suggestions(
    suggestions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    seen = set()
    deduplicated = []

    for suggestion in suggestions:
        key = (
            suggestion.get("question"),
            suggestion.get("expected_analysis_type"),
            suggestion.get("required_capability", {}).get("metric"),
            suggestion.get("required_capability", {}).get("dimension"),
        )

        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(suggestion)

    return deduplicated


def _first_drilldown(
    structured_insight: Dict[str, Any],
    analysis_type: str,
) -> Optional[Dict[str, Any]]:
    for drilldown in structured_insight.get("available_drilldowns", []):
        if drilldown.get("analysis_type") == analysis_type:
            return drilldown

    return None
