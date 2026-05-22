import json
import time
from pathlib import Path
from typing import Any, Dict


TRACE_DIR = Path("traces")
TRACE_DIR.mkdir(exist_ok=True)


def now_ms() -> int:
    return int(time.time() * 1000)


def write_trace(request_id: str, trace: Dict[str, Any]) -> str:
    path = TRACE_DIR / f"{request_id}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(trace, f, ensure_ascii=False, indent=2)

    return str(path)