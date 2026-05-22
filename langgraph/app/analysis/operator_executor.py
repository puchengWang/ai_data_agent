from typing import Any, Dict, List

from app.analysis.operator_mapping import get_operators_for_aggregation
from app.analysis.operator_registry import OPERATOR_REGISTRY


def execute_analysis_operators(
    aggregation_type: str,
    analysis_input: Dict[str, Any],
) -> Dict[str, Any]:
    operator_names = get_operators_for_aggregation(aggregation_type)

    operator_results = {}

    for operator_name in operator_names:
        operator = OPERATOR_REGISTRY.get(operator_name)

        if not operator:
            operator_results[operator_name] = {
                "success": False,
                "error": f"Unknown operator: {operator_name}",
                "data": None,
            }
            continue

        try:
            operator_results[operator_name] = {
                "success": True,
                "error": None,
                "data": run_operator(
                    operator_name=operator_name,
                    operator=operator,
                    aggregation_type=aggregation_type,
                    analysis_input=analysis_input,
                ),
            }

        except Exception as e:
            operator_results[operator_name] = {
                "success": False,
                "error": str(e),
                "data": None,
            }

    return operator_results


def run_operator(
    operator_name: str,
    operator,
    aggregation_type: str,
    analysis_input: Dict[str, Any],
) -> Any:
    if operator_name == "growth_rate":
        return run_growth_rate_operator(
            operator=operator,
            aggregation_type=aggregation_type,
            analysis_input=analysis_input,
        )

    if operator_name in ["peak_valley", "volatility", "basic_anomaly"]:
        return run_time_series_operator(
            operator=operator,
            aggregation_type=aggregation_type,
            analysis_input=analysis_input,
        )

    if operator_name == "contribution":
        return run_contribution_operator(
            operator=operator,
            aggregation_type=aggregation_type,
            analysis_input=analysis_input,
        )

    raise ValueError(f"Unsupported operator execution: {operator_name}")


def run_growth_rate_operator(
    operator,
    aggregation_type: str,
    analysis_input: Dict[str, Any],
) -> Any:
    if aggregation_type == "compare":
        return operator(
            current_value=analysis_input["current_value"],
            previous_value=analysis_input["previous_value"],
        )

    if aggregation_type == "compare_by_dimension":
        rows = []

        for row in analysis_input.get("rows", []):
            result = operator(
                current_value=row["current_value"],
                previous_value=row["previous_value"],
            )

            rows.append({
                **row,
                "change": result["change"],
                "change_rate": result["change_rate"],
                "direction": result["direction"],
            })

        return {
            "rows": rows
        }

    raise ValueError(f"growth_rate does not support aggregation_type={aggregation_type}")


def run_time_series_operator(
    operator,
    aggregation_type: str,
    analysis_input: Dict[str, Any],
) -> Any:
    if aggregation_type == "trend":
        return operator(
            analysis_input.get("time_series", [])
        )

    if aggregation_type == "trend_by_dimension":
        result = {}

        series = analysis_input.get("series", {})

        for dimension_value, time_series in series.items():
            result[dimension_value] = operator(time_series)

        return result

    raise ValueError(
        f"time_series operator does not support aggregation_type={aggregation_type}"
    )


def run_contribution_operator(
    operator,
    aggregation_type: str,
    analysis_input: Dict[str, Any],
) -> Any:
    if aggregation_type in ["group_by", "top_n", "distribution"]:
        return operator(
            analysis_input.get("rows", [])
        )

    raise ValueError(
        f"contribution does not support aggregation_type={aggregation_type}"
    )