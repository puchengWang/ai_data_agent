from typing import Any, Dict, List, Optional


def find_peak_valley(time_series: List[Dict[str, Any]]) -> Dict[str, Optional[Dict[str, Any]]]:
    valid_points = [
        item for item in time_series
        if item.get("value") is not None
    ]

    if not valid_points:
        return {
            "peak": None,
            "valley": None
        }

    peak = max(valid_points, key=lambda x: x["value"])
    valley = min(valid_points, key=lambda x: x["value"])

    return {
        "peak": peak,
        "valley": valley
    }