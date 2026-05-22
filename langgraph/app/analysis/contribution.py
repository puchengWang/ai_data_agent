from typing import Any, Dict, List


def calculate_contribution(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid_rows = [
        row for row in rows
        if row.get("value") is not None
    ]

    total_value = sum(row.get("value", 0) or 0 for row in valid_rows)

    contribution_rows = []

    for row in valid_rows:
        value = row.get("value", 0) or 0

        if total_value == 0:
            contribution_rate = None
        else:
            contribution_rate = round(value / total_value * 100, 2)

        contribution_rows.append({
            "dimension_value": row.get("dimension_value"),
            "value": value,
            "contribution_rate": contribution_rate,
        })

    top_contributor = None

    if contribution_rows:
        top_contributor = max(
            contribution_rows,
            key=lambda x: x["value"]
        )

    return {
        "total_value": total_value,
        "rows": contribution_rows,
        "top_contributor": top_contributor,
    }