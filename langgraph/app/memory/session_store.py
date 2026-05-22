import json
from pathlib import Path
from typing import Any, Dict


SESSION_DIR = Path("sessions")
SESSION_DIR.mkdir(exist_ok=True)


def get_session_path(session_id: str) -> Path:
    return SESSION_DIR / f"{session_id}.json"


def load_session(session_id: str) -> Dict[str, Any]:
    path = get_session_path(session_id)

    if not path.exists():
        return {
            "session_id": session_id,
            "turns": [],
            "last_context": {}
        }

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_session(session_id: str, session_data: Dict[str, Any]) -> None:
    path = get_session_path(session_id)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)