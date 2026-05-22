from typing import Any, Dict, List


def detect_basic_anomaly(
    time_series: List[Dict[str, Any]],
    threshold_ratio: float = 0.3,
) -> Dict[str, Any]:
    valid_points = [
        item for item in time_series
        if item.get("value") is not None
    ]

    values = [item["value"] for item in valid_points]

    if len(values) < 3:
        return {
            "has_anomaly": False,
            "reason": "not_enough_data",
            "anomalies": [],
        }

    avg_value = sum(values) / len(values)

    anomalies = []

    for item in valid_points:
        value = item["value"]

        if avg_value == 0:
            continue

        diff_ratio = (value - avg_value) / avg_value

        if abs(diff_ratio) >= threshold_ratio:
            anomalies.append({
                "time_label": item.get("time_label"),
                "value": value,
                "avg_value": round(avg_value, 2),
                "diff_ratio": round(diff_ratio * 100, 2),
                "direction": "up" if diff_ratio > 0 else "down",
            })

    return {
        "has_anomaly": len(anomalies) > 0,
        "method": "avg_diff_ratio",
        "threshold_ratio": threshold_ratio,
        "avg_value": round(avg_value, 2),
        "anomalies": anomalies,
    }