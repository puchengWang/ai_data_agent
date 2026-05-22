import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.graph import build_graph  # noqa: E402


TEST_CASE_FILE = PROJECT_ROOT / "tests" / "follow_up_cases.yaml"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "outputs"
SNAPSHOT_DIR = PROJECT_ROOT / "tests" / "snapshots" / "follow_up"
SESSION_DIR = PROJECT_ROOT / "sessions"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
SESSION_DIR.mkdir(parents=True, exist_ok=True)


def load_cases() -> List[Dict[str, Any]]:
    if not TEST_CASE_FILE.exists():
        raise FileNotFoundError(f"Follow-up test case file not found: {TEST_CASE_FILE}")

    with open(TEST_CASE_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data.get("cases", [])


def delete_session_file(session_id: str) -> None:
    path = SESSION_DIR / f"{session_id}.json"

    if path.exists():
        path.unlink()


def get_context_used(result: Dict[str, Any]) -> bool:
    trace = result.get("trace", {})

    if "context_used" in trace:
        return bool(trace.get("context_used"))

    return bool(
        result.get("is_follow_up")
        and result.get("inherited_context")
    )


def validate_turn(
    expected: Dict[str, Any],
    result: Dict[str, Any],
) -> List[str]:
    errors = []

    if "expected_is_follow_up" in expected:
        actual = bool(result.get("is_follow_up"))
        expected_value = bool(expected["expected_is_follow_up"])

        if actual != expected_value:
            errors.append(
                f"is_follow_up mismatch: expected={expected_value}, actual={actual}"
            )

    if "expected_reset_context" in expected:
        actual = bool(result.get("reset_context"))
        expected_value = bool(expected["expected_reset_context"])

        if actual != expected_value:
            errors.append(
                f"reset_context mismatch: expected={expected_value}, actual={actual}"
            )

    if "expected_context_used" in expected:
        actual = get_context_used(result)
        expected_value = bool(expected["expected_context_used"])

        if actual != expected_value:
            errors.append(
                f"context_used mismatch: expected={expected_value}, actual={actual}"
            )

    if "expected_memory_only" in expected:
        actual = bool(result.get("used_memory_only"))
        expected_value = bool(expected["expected_memory_only"])

        if actual != expected_value:
            errors.append(
                f"used_memory_only mismatch: expected={expected_value}, actual={actual}"
            )

    if "expected_aggregation_type" in expected:
        actual = (
            result.get("aggregation_plan", {})
            .get("aggregation_type")
        )
        expected_value = expected["expected_aggregation_type"]

        if actual != expected_value:
            errors.append(
                f"aggregation_type mismatch: expected={expected_value}, actual={actual}"
            )

    if not result.get("answer"):
        errors.append("answer is empty")

    return errors


def save_turn_snapshot(case_name: str, turn_index: int, result: Dict[str, Any]) -> str:
    path = SNAPSHOT_DIR / f"{case_name}_turn_{turn_index}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return str(path)


def run_case(graph, case: Dict[str, Any]) -> Dict[str, Any]:
    case_name = case["name"]
    session_id = case["session_id"]
    turns = case.get("turns", [])

    delete_session_file(session_id)

    case_errors = []
    turn_results = []

    for index, turn in enumerate(turns, start=1):
        request_id = f"follow-up-{case_name}-turn-{index}-{int(time.time())}"

        start_time = time.time()

        try:
            result = graph.invoke({
                "session_id": session_id,
                "question": turn["question"],
                "request_id": request_id,
            })

            duration_ms = int((time.time() - start_time) * 1000)

            errors = validate_turn(turn, result)

            snapshot_path = save_turn_snapshot(case_name, index, result)

            turn_result = {
                "turn": index,
                "question": turn["question"],
                "success": len(errors) == 0,
                "errors": errors,
                "duration_ms": duration_ms,
                "is_follow_up": result.get("is_follow_up"),
                "reset_context": result.get("reset_context"),
                "context_used": get_context_used(result),
                "used_memory_only": result.get("used_memory_only", False),
                "aggregation_type": result.get("aggregation_plan", {}).get("aggregation_type"),
                "snapshot_path": snapshot_path,
                "answer": result.get("answer"),
            }

            if errors:
                case_errors.extend([f"turn {index}: {e}" for e in errors])

            turn_results.append(turn_result)

        except Exception as e:
            case_errors.append(f"turn {index}: {str(e)}")

            turn_results.append({
                "turn": index,
                "question": turn["question"],
                "success": False,
                "errors": [str(e)],
                "duration_ms": int((time.time() - start_time) * 1000),
                "snapshot_path": None,
                "answer": None,
            })

    return {
        "case_name": case_name,
        "session_id": session_id,
        "success": len(case_errors) == 0,
        "errors": case_errors,
        "turns": turn_results,
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

    report_path = OUTPUT_DIR / "latest_follow_up_regression_report.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    summary_path = OUTPUT_DIR / "latest_follow_up_regression_summary.txt"

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"Total: {total}\n")
        f.write(f"Passed: {passed}\n")
        f.write(f"Failed: {failed}\n\n")

        for case in results:
            status = "PASS" if case["success"] else "FAIL"
            f.write(f"[{status}] {case['case_name']}\n")

            for turn in case["turns"]:
                f.write(f"  Turn {turn['turn']}: {turn['question']}\n")
                f.write(f"    is_follow_up: {turn.get('is_follow_up')}\n")
                f.write(f"    reset_context: {turn.get('reset_context')}\n")
                f.write(f"    context_used: {turn.get('context_used')}\n")
                f.write(f"    used_memory_only: {turn.get('used_memory_only')}\n")
                f.write(f"    aggregation_type: {turn.get('aggregation_type')}\n")

                if turn.get("errors"):
                    f.write(f"    errors: {turn['errors']}\n")

            f.write("\n")

    print(f"\nFollow-up regression report written to: {report_path}")
    print(f"Follow-up regression summary written to: {summary_path}")


def main():
    cases = load_cases()

    if not cases:
        raise ValueError("No follow-up test cases found")

    graph = build_graph()

    results = []

    print(f"Running {len(cases)} follow-up regression cases...\n")

    for case in cases:
        print(f"Running case: {case['name']}")

        result = run_case(graph, case)

        results.append(result)

        status = "PASS" if result["success"] else "FAIL"
        print(f"  {status}")

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