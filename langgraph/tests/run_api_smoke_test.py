import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a smoke test against the FastAPI runtime app.",
    )
    parser.add_argument(
        "--real-bedrock",
        action="store_true",
        help="Use real Bedrock instead of mock Bedrock.",
    )
    parser.add_argument(
        "--question",
        default="2026-05-21新增用户量是多少",
    )
    parser.add_argument(
        "--session-id",
        default="api-smoke-test",
    )
    return parser.parse_args()


def main() -> None:
    try:
        from fastapi.testclient import TestClient
    except ImportError as e:
        raise SystemExit(
            "FastAPI test dependencies are not installed. "
            "Install requirements.txt first."
        ) from e

    from app.api import app

    args = parse_args()
    client = TestClient(app)

    response = client.post("/analyze", json={
        "session_id": args.session_id,
        "question": args.question,
        "mock_bedrock": not args.real_bedrock,
        "debug": True,
    })

    payload = response.json()

    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if response.status_code != 200:
        raise SystemExit(1)

    if not payload.get("success"):
        raise SystemExit(1)

    if not payload.get("structured_insight"):
        raise SystemExit("structured_insight is missing")

    if not isinstance(payload.get("follow_up_suggestions"), list):
        raise SystemExit("follow_up_suggestions must be a list")


if __name__ == "__main__":
    main()
