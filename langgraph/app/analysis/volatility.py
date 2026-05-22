from typing import Any, Dict, List
import statistics


def calculate_volatility(time_series: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid_points = [
        item for item in time_series
        if item.get("value") is not None
    ]

    values = [item["value"] for item in valid_points]

    if not values:
        return {
            "avg": None,
            "stddev": None,
            "min": None,
            "max": None,
            "range": None,
            "volatility_level": "unknown",
        }

    avg_value = round(sum(values) / len(values), 2)
    min_value = min(values)
    max_value = max(values)
    value_range = max_value - min_value

    if len(values) >= 2:
        stddev = round(statistics.stdev(values), 2)
    else:
        stddev = 0

    if avg_value == 0:
        volatility_ratio = None
    else:
        volatility_ratio = round(stddev / avg_value * 100, 2)

    if volatility_ratio is None:
        volatility_level = "unknown"
    elif volatility_ratio < 10:
        volatility_level = "low"
    elif volatility_ratio < 30:
        volatility_level = "medium"
    else:
        volatility_level = "high"

    return {
        "avg": avg_value,
        "stddev": stddev,
        "min": min_value,
        "max": max_value,
        "range": value_range,
        "volatility_ratio": volatility_ratio,
        "volatility_level": volatility_level,
    }