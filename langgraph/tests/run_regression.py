import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml


# 确保可以从项目根目录导入 app
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.graph import build_graph  # noqa: E402


TEST_CASE_FILE = PROJECT_ROOT / "tests" / "test_cases.yaml"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "outputs"
SNAPSHOT_DIR = PROJECT_ROOT / "tests" / "snapshots"


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def load_test_cases() -> List[Dict[str, Any]]:
    if not TEST_CASE_FILE.exists():
        raise FileNotFoundError(f"Test case file not found: {TEST_CASE_FILE}")

    with open(TEST_CASE_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data.get("cases", [])


def contains_sql_keyword(query_plans: List[Dict[str, Any]], keyword: str) -> bool:
    keyword_lower = keyword.lower()

    for plan in query_plans:
        sql = plan.get("sql", "")
        if keyword_lower in sql.lower():
            return True

    return False


def validate_case_result(
    case: Dict[str, Any],
    result: Dict[str, Any],
) -> Dict[str, Any]:

    errors = []

    expected_aggregation_type = case.get("expected_aggregation_type")
    actual_aggregation_type = (
        result.get("aggregation_plan", {}).get("aggregation_type")
    )

    if expected_aggregation_type and actual_aggregation_type != expected_aggregation_type:
        errors.append(
            f"aggregation_type mismatch: expected={expected_aggregation_type}, actual={actual_aggregation_type}"
        )

    query_plans = result.get("query_plans", [])

    if not query_plans:
        errors.append("query_plans is empty")

    expected_sql_keywords = case.get("expected_sql_keywords", [])

    for keyword in expected_sql_keywords:
        if not contains_sql_keyword(query_plans, keyword):
            errors.append(f"SQL keyword not found: {keyword}")

    tool_results = result.get("tool_results", [])

    if not tool_results:
        errors.append("tool_results is empty")

    failed_tool_results = [
        item for item in tool_results
        if not item.get("success")
    ]

    if failed_tool_results:
        errors.append(
            f"tool_results contains failed tasks: {len(failed_tool_results)}"
        )

    expected_operators = case.get("expected_operators", [])
    
    operator_results = (
        result.get("aggregation_result", {})
        .get("operator_results", {})
    )
    
    for operator_name in expected_operators:
        operator_result = operator_results.get(operator_name)
    
        if not operator_result:
            errors.append(f"operator_result not found: {operator_name}")
            continue
    
        if not operator_result.get("success"):
            errors.append(
                f"operator_result failed: {operator_name}, error={operator_result.get('error')}"
            )

    answer = result.get("answer")

    if not answer:
        errors.append("answer is empty")

    return {
        "success": len(errors) == 0,
        "errors": errors,
        "actual_aggregation_type": actual_aggregation_type,
        "query_plan_count": len(query_plans),
        "tool_result_count": len(tool_results),
        "operator_result_count": len(operator_results),
        "operator_results": list(operator_results.keys()),
        "answer": answer,
    }


def save_snapshot(case_name: str, result: Dict[str, Any]) -> str:
    path = SNAPSHOT_DIR / f"{case_name}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return str(path)


def run_case(graph, case: Dict[str, Any]) -> Dict[str, Any]:
    case_name = case["name"]
    question = case["question"]

    request_id = f"regression-{case_name}-{int(time.time())}"

    start_time = time.time()

    try:
        result = graph.invoke({
            "question": question,
            "request_id": request_id,
        })

        duration_ms = int((time.time() - start_time) * 1000)

        validation = validate_case_result(case, result)

        snapshot_path = save_snapshot(case_name, result)

        return {
            "case_name": case_name,
            "question": question,
            "success": validation["success"],
            "errors": validation["errors"],
            "duration_ms": duration_ms,
            "expected_aggregation_type": case.get("expected_aggregation_type"),
            "actual_aggregation_type": validation["actual_aggregation_type"],
            "expected_operators": case.get("expected_operators", []),
            "actual_operators": validation["operator_results"],
            "operator_result_count": validation["operator_result_count"],
            "query_plan_count": validation["query_plan_count"],
            "tool_result_count": validation["tool_result_count"],
            "snapshot_path": snapshot_path,
            "answer": validation["answer"],
        }

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "case_name": case_name,
            "question": question,
            "success": False,
            "errors": [str(e)],
            "duration_ms": duration_ms,
            "expected_aggregation_type": case.get("expected_aggregation_type"),
            "actual_aggregation_type": None,
            "query_plan_count": 0,
            "tool_result_count": 0,
            "snapshot_path": None,
            "answer": None,
        }


def write_report(results: List[Dict[str, Any]]) -> None:
    total = len(results)
    passed = len([r for r in results if r["success"]])
    failed = total - passed

    report = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "results": results,
    }

    report_path = OUTPUT_DIR / "latest_regression_report.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    summary_path = OUTPUT_DIR / "latest_regression_summary.txt"

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"Total: {total}\n")
        f.write(f"Passed: {passed}\n")
        f.write(f"Failed: {failed}\n\n")

        for r in results:
            status = "PASS" if r["success"] else "FAIL"
            f.write(f"[{status}] {r['case_name']}\n")
            f.write(f"  question: {r['question']}\n")
            f.write(f"  expected: {r['expected_aggregation_type']}\n")
            f.write(f"  actual: {r['actual_aggregation_type']}\n")
            f.write(f"  duration_ms: {r['duration_ms']}\n")
            f.write(f"  expected_operators: {r.get('expected_operators')}\n")
            f.write(f"  actual_operators: {r.get('actual_operators')}\n")

            if r["errors"]:
                f.write(f"  errors: {r['errors']}\n")

            f.write("\n")

    print(f"\nRegression report written to: {report_path}")
    print(f"Regression summary written to: {summary_path}")


def main():
    cases = load_test_cases()

    if not cases:
        raise ValueError("No test cases found in tests/test_cases.yaml")

    graph = build_graph()

    results = []

    print(f"Running {len(cases)} regression cases...\n")

    for case in cases:
        print(f"Running case: {case['name']}")

        result = run_case(graph, case)

        results.append(result)

        status = "PASS" if result["success"] else "FAIL"

        print(
            f"  {status} | aggregation_type={result['actual_aggregation_type']} | duration={result['duration_ms']}ms"
        )

        if result["errors"]:
            for error in result["errors"]:
                print(f"  - {error}")

        print()

    write_report(results)

    failed = [r for r in results if not r["success"]]

    if failed:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()