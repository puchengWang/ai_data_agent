import json
from pathlib import Path
from typing import Any, Dict


SESSION_DIR = Path("sessions")
SESSION_DIR.mkdir(exist_ok=True)


def get_session_path(session_id: str) -> Path:
    return SESSION_DIR / f"{session_id}.json"


def default_session_data(session_id: str) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "turns": [],
        "last_context": {},
        "last_analysis_context": {},
        "last_answer": {},
        "last_follow_up_suggestions": [],
    }


def normalize_session_data(
    session_id: str,
    session_data: Dict[str, Any],
) -> Dict[str, Any]:
    normalized = default_session_data(session_id)
    normalized.update(session_data or {})

    if not normalized.get("last_analysis_context") and normalized.get("last_context"):
        last_context = normalized.get("last_context") or {}
        if last_context.get("aggregation_result"):
            normalized["last_analysis_context"] = last_context

    if not isinstance(normalized.get("last_answer"), dict):
        normalized["last_answer"] = {}

    if not isinstance(normalized.get("last_follow_up_suggestions"), list):
        normalized["last_follow_up_suggestions"] = []

    return normalized


def load_session(session_id: str) -> Dict[str, Any]:
    path = get_session_path(session_id)

    if not path.exists():
        return default_session_data(session_id)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return normalize_session_data(session_id, data)


def save_session(session_id: str, session_data: Dict[str, Any]) -> None:
    path = get_session_path(session_id)
    normalized = normalize_session_data(session_id, session_data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
