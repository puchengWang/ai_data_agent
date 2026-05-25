import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import app.graph as graph_module  # noqa: E402
import app.memory.context_strategy as context_strategy_module  # noqa: E402


TEST_CASE_FILE = PROJECT_ROOT / "tests" / "follow_up_cases.yaml"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "outputs"
SNAPSHOT_DIR = PROJECT_ROOT / "tests" / "snapshots" / "follow_up"
SESSION_DIR = PROJECT_ROOT / "sessions"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
SESSION_DIR.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run follow-up regression cases.",
    )
    parser.add_argument(
        "--mock-bedrock",
        action="store_true",
        help="Mock Bedrock parsing, context strategy, and memory-only answers.",
    )
    return parser.parse_args()


def mock_bedrock_json(prompt: str) -> Dict[str, Any]:
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


def mock_bedrock_text(prompt: str) -> str:
    return (
        "Mock Bedrock memory answer: 真实 Bedrock 当前不可用，"
        "本次仅用于验证 follow-up memory 行为。"
    )


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

    if _has_complete_date_range(question):
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


def install_bedrock_mocks() -> None:
    graph_module.invoke_bedrock_json = mock_bedrock_json
    graph_module.invoke_bedrock_text = mock_bedrock_text
    context_strategy_module.invoke_bedrock_json = mock_context_strategy_json


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


def _has_complete_date_range(question: str) -> bool:
    date_matches = re.findall(r"\d{4}-\d{2}-\d{2}", question)
    return bool(date_matches)


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


def load_session_file(session_id: str) -> Dict[str, Any]:
    path = SESSION_DIR / f"{session_id}.json"

    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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


def validate_session_after_turn(
    expected: Dict[str, Any],
    session_data: Dict[str, Any],
) -> List[str]:
    errors = []

    last_analysis_context = (
        session_data.get("last_analysis_context")
        or {}
    )
    last_answer = session_data.get("last_answer") or {}
    last_follow_up_suggestions = (
        session_data.get("last_follow_up_suggestions")
        or []
    )

    if "expected_last_analysis_type" in expected:
        actual = last_analysis_context.get("aggregation_type")
        expected_value = expected["expected_last_analysis_type"]

        if actual != expected_value:
            errors.append(
                "last_analysis_context aggregation_type mismatch: "
                f"expected={expected_value}, actual={actual}"
            )

    if "expected_last_analysis_question" in expected:
        actual = last_analysis_context.get("question")
        expected_value = expected["expected_last_analysis_question"]

        if actual != expected_value:
            errors.append(
                "last_analysis_context question mismatch: "
                f"expected={expected_value}, actual={actual}"
            )

    if "expected_last_answer_question" in expected:
        actual = last_answer.get("question")
        expected_value = expected["expected_last_answer_question"]

        if actual != expected_value:
            errors.append(
                "last_answer question mismatch: "
                f"expected={expected_value}, actual={actual}"
            )

    if expected.get("expected_last_analysis_type"):
        if "structured_insight" not in last_analysis_context:
            errors.append("last_analysis_context missing structured_insight")

        if "follow_up_suggestions" not in last_analysis_context:
            errors.append("last_analysis_context missing follow_up_suggestions")

        if not isinstance(last_follow_up_suggestions, list):
            errors.append("last_follow_up_suggestions must be a list")

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
            session_data = load_session_file(session_id)
            session_errors = validate_session_after_turn(turn, session_data)
            errors.extend(session_errors)

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
                "last_analysis_type": (
                    session_data.get("last_analysis_context", {})
                    .get("aggregation_type")
                ),
                "last_analysis_question": (
                    session_data.get("last_analysis_context", {})
                    .get("question")
                ),
                "last_answer_question": (
                    session_data.get("last_answer", {})
                    .get("question")
                ),
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
                f.write(f"    last_analysis_type: {turn.get('last_analysis_type')}\n")
                f.write(f"    last_analysis_question: {turn.get('last_analysis_question')}\n")
                f.write(f"    last_answer_question: {turn.get('last_answer_question')}\n")

                if turn.get("errors"):
                    f.write(f"    errors: {turn['errors']}\n")

            f.write("\n")

    print(f"\nFollow-up regression report written to: {report_path}")
    print(f"Follow-up regression summary written to: {summary_path}")


def main():
    args = parse_args()

    if args.mock_bedrock:
        install_bedrock_mocks()

    cases = load_cases()

    if not cases:
        raise ValueError("No follow-up test cases found")

    graph = graph_module.build_graph()

    results = []

    mode = "mock_bedrock" if args.mock_bedrock else "real_bedrock"
    print(f"Running {len(cases)} follow-up regression cases...")
    print(f"mode: {mode}\n")

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
