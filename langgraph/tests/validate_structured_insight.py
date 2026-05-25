import json
import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = PROJECT_ROOT / "tests" / "snapshots"

sys.path.insert(0, str(PROJECT_ROOT))

from app.insight.structured_insight import build_structured_insight  # noqa: E402


SNAPSHOT_CASES = {
    "normal_user_count": "scalar_value",
    "compare_user_count": "period_compare",
    "trend_user_count": "trend_summary",
    "group_by_level": "contribution",
    "top_n_level": "contribution",
    "distribution_level": "contribution",
    "compare_by_dimension_level": "dimension_compare",
    "trend_by_dimension_level": "dimension_trend",
}

REQUIRED_KEYS = {
    "main_conclusion",
    "evidence",
    "interesting_points",
    "limitations",
    "available_drilldowns",
    "suggestion_context",
}

ALLOWED_DRILLDOWN_DIMENSIONS = {
    None,
    "level",
}


def add_error(errors: List[str], message: str) -> None:
    errors.append(f"[ERROR] {message}")


def load_snapshot(case_name: str) -> Dict[str, Any]:
    path = SNAPSHOT_DIR / f"{case_name}.json"

    if not path.exists():
        raise FileNotFoundError(f"Missing snapshot: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_required_shape(
    case_name: str,
    insight: Dict[str, Any],
    errors: List[str],
) -> None:
    missing_keys = REQUIRED_KEYS - set(insight.keys())
    if missing_keys:
        add_error(errors, f"{case_name}: missing keys: {sorted(missing_keys)}")

    if not insight.get("main_conclusion"):
        add_error(errors, f"{case_name}: main_conclusion is empty")

    if not isinstance(insight.get("evidence"), list):
        add_error(errors, f"{case_name}: evidence must be a list")

    if not isinstance(insight.get("interesting_points"), list):
        add_error(errors, f"{case_name}: interesting_points must be a list")

    if not isinstance(insight.get("limitations"), list):
        add_error(errors, f"{case_name}: limitations must be a list")

    if not isinstance(insight.get("available_drilldowns"), list):
        add_error(errors, f"{case_name}: available_drilldowns must be a list")

    if not isinstance(insight.get("suggestion_context"), dict):
        add_error(errors, f"{case_name}: suggestion_context must be a dict")


def validate_expected_evidence(
    case_name: str,
    expected_evidence_type: str,
    insight: Dict[str, Any],
    errors: List[str],
) -> None:
    evidence_types = {
        item.get("type")
        for item in insight.get("evidence", [])
    }

    if expected_evidence_type not in evidence_types:
        add_error(
            errors,
            f"{case_name}: expected evidence type not found: {expected_evidence_type}",
        )


def validate_capability_bounds(
    case_name: str,
    insight: Dict[str, Any],
    errors: List[str],
) -> None:
    suggestion_context = insight.get("suggestion_context", {})

    if suggestion_context.get("metric") != "user_count":
        add_error(
            errors,
            f"{case_name}: unexpected metric: {suggestion_context.get('metric')}",
        )

    dimensions = suggestion_context.get("available_dimensions", [])
    if dimensions != ["level"]:
        add_error(
            errors,
            f"{case_name}: unexpected available dimensions: {dimensions}",
        )

    for drilldown in insight.get("available_drilldowns", []):
        dimension = drilldown.get("dimension")
        if dimension not in ALLOWED_DRILLDOWN_DIMENSIONS:
            add_error(
                errors,
                f"{case_name}: unsupported drilldown dimension: {dimension}",
            )

        if drilldown.get("metric") != "user_count":
            add_error(
                errors,
                f"{case_name}: unsupported drilldown metric: {drilldown.get('metric')}",
            )


def validate_snapshot_case(
    case_name: str,
    expected_evidence_type: str,
) -> Dict[str, Any]:
    snapshot = load_snapshot(case_name)
    insight = build_structured_insight(
        question=snapshot.get("question", ""),
        aggregation_plan=snapshot.get("aggregation_plan", {}),
        aggregation_result=snapshot.get("aggregation_result", {}),
        tool_results=snapshot.get("tool_results", []),
    )

    errors = []
    validate_required_shape(case_name, insight, errors)
    validate_expected_evidence(case_name, expected_evidence_type, insight, errors)
    validate_capability_bounds(case_name, insight, errors)

    return {
        "case_name": case_name,
        "success": not errors,
        "errors": errors,
        "main_conclusion": insight.get("main_conclusion"),
        "evidence_types": [
            item.get("type")
            for item in insight.get("evidence", [])
        ],
        "drilldown_count": len(insight.get("available_drilldowns", [])),
    }


def main() -> None:
    results = [
        validate_snapshot_case(case_name, expected_evidence_type)
        for case_name, expected_evidence_type in SNAPSHOT_CASES.items()
    ]

    failed = [
        result for result in results
        if not result["success"]
    ]

    print("\nStructured Insight Validation Result")
    print("=" * 40)

    for result in results:
        status = "PASS" if result["success"] else "FAIL"
        print(f"[{status}] {result['case_name']}")
        print(f"  evidence_types: {result['evidence_types']}")
        print(f"  drilldown_count: {result['drilldown_count']}")
        print(f"  main_conclusion: {result['main_conclusion']}")

        for error in result["errors"]:
            print(f"  {error}")

    print("\nSummary:")
    print(f"total: {len(results)}")
    print(f"failed: {len(failed)}")

    if failed:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
