import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.memory.session_store import normalize_session_data  # noqa: E402


def add_error(errors: list[str], message: str) -> None:
    errors.append(f"[ERROR] {message}")


def main() -> None:
    errors = []

    session = normalize_session_data("test-session", {
        "session_id": "test-session",
        "turns": [],
        "last_context": {
            "question": "old question",
            "aggregation_result": {"ok": True},
            "structured_insight": {"main_conclusion": "old insight"},
            "follow_up_suggestions": [{"question": "next"}],
        },
    })

    if "last_analysis_context" not in session:
        add_error(errors, "missing last_analysis_context")

    if not session["last_analysis_context"]:
        add_error(
            errors,
            "legacy last_context was not promoted to last_analysis_context",
        )

    if "last_answer" not in session:
        add_error(errors, "missing last_answer")

    if "last_follow_up_suggestions" not in session:
        add_error(errors, "missing last_follow_up_suggestions")

    if not isinstance(session["last_follow_up_suggestions"], list):
        add_error(errors, "last_follow_up_suggestions must be a list")

    print("\nMemory Context Refinement Validation Result")
    print("=" * 40)

    for error in errors:
        print(error)

    print("\nSummary:")
    print(f"errors: {len(errors)}")

    if errors:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
