import json
import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = PROJECT_ROOT / "tests" / "snapshots"

sys.path.insert(0, str(PROJECT_ROOT))

from app.capabilities.catalog import (  # noqa: E402
    build_capability_catalog,
    validate_capability,
)
from app.follow_up.suggestion_generator import (  # noqa: E402
    generate_follow_up_suggestions,
)
from app.insight.structured_insight import build_structured_insight  # noqa: E402


SNAPSHOT_CASES = [
    "normal_user_count",
    "compare_user_count",
    "trend_user_count",
    "group_by_level",
    "top_n_level",
    "distribution_level",
    "compare_by_dimension_level",
    "trend_by_dimension_level",
]

UNSUPPORTED_TERMS = [
    "channel",
    "region",
    "device",
    "revenue",
]


def add_error(errors: List[str], message: str) -> None:
    errors.append(f"[ERROR] {message}")


def load_snapshot(case_name: str) -> Dict[str, Any]:
    path = SNAPSHOT_DIR / f"{case_name}.json"

    if not path.exists():
        raise FileNotFoundError(f"Missing snapshot: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_suggestion_shape(
    case_name: str,
    suggestion: Dict[str, Any],
    errors: List[str],
) -> None:
    if not suggestion.get("question"):
        add_error(errors, f"{case_name}: suggestion question is empty")

    if not suggestion.get("reason"):
        add_error(errors, f"{case_name}: suggestion reason is empty")

    if not suggestion.get("expected_analysis_type"):
        add_error(errors, f"{case_name}: expected_analysis_type is empty")

    required_capability = suggestion.get("required_capability")
    if not isinstance(required_capability, dict):
        add_error(errors, f"{case_name}: required_capability must be a dict")
        return

    if not required_capability.get("metric"):
        add_error(errors, f"{case_name}: required metric is empty")


def validate_capability_bounds(
    case_name: str,
    suggestion: Dict[str, Any],
    catalog: Dict[str, Any],
    errors: List[str],
) -> None:
    required = suggestion.get("required_capability", {})

    validation = validate_capability(
        metric=required.get("metric"),
        analysis_type=suggestion.get("expected_analysis_type"),
        dimension=required.get("dimension"),
        catalog=catalog,
    )

    if not validation["valid"]:
        add_error(
            errors,
            f"{case_name}: invalid suggestion capability: {validation['errors']}",
        )

    serialized = json.dumps(suggestion, ensure_ascii=False)
    for unsupported in UNSUPPORTED_TERMS:
        if unsupported in serialized:
            add_error(
                errors,
                f"{case_name}: unsupported capability leaked: {unsupported}",
            )


def validate_case(
    case_name: str,
    catalog: Dict[str, Any],
) -> Dict[str, Any]:
    snapshot = load_snapshot(case_name)
    insight = build_structured_insight(
        question=snapshot.get("question", ""),
        aggregation_plan=snapshot.get("aggregation_plan", {}),
        aggregation_result=snapshot.get("aggregation_result", {}),
        tool_results=snapshot.get("tool_results", []),
        capability_catalog=catalog,
    )

    suggestions = generate_follow_up_suggestions(
        structured_insight=insight,
        capability_catalog=catalog,
    )

    errors = []

    if len(suggestions) > 4:
        add_error(errors, f"{case_name}: too many suggestions: {len(suggestions)}")

    seen_questions = set()
    for suggestion in suggestions:
        question = suggestion.get("question")

        if question in seen_questions:
            add_error(errors, f"{case_name}: duplicate question: {question}")

        seen_questions.add(question)

        validate_suggestion_shape(case_name, suggestion, errors)
        validate_capability_bounds(case_name, suggestion, catalog, errors)

    return {
        "case_name": case_name,
        "success": not errors,
        "errors": errors,
        "suggestion_count": len(suggestions),
        "expected_analysis_types": [
            suggestion.get("expected_analysis_type")
            for suggestion in suggestions
        ],
        "questions": [
            suggestion.get("question")
            for suggestion in suggestions
        ],
    }


def main() -> None:
    catalog = build_capability_catalog()
    results = [
        validate_case(case_name, catalog)
        for case_name in SNAPSHOT_CASES
    ]

    failed = [
        result for result in results
        if not result["success"]
    ]

    print("\nFollow-up Suggestions Validation Result")
    print("=" * 40)

    for result in results:
        status = "PASS" if result["success"] else "FAIL"
        print(f"[{status}] {result['case_name']}")
        print(f"  suggestion_count: {result['suggestion_count']}")
        print(f"  expected_analysis_types: {result['expected_analysis_types']}")
        for question in result["questions"]:
            print(f"  question: {question}")

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
