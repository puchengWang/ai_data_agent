def calculate_growth_rate(
    current_value: float | int | None,
    previous_value: float | int | None,
) -> dict:

    current_value = current_value or 0
    previous_value = previous_value or 0

    change = current_value - previous_value

    if previous_value == 0:
        change_rate = None
    else:
        change_rate = round(
            (change / previous_value) * 100,
            2,
        )

    if change > 0:
        direction = "up"
    elif change < 0:
        direction = "down"
    else:
        direction = "flat"

    return {
        "current_value": current_value,
        "previous_value": previous_value,
        "change": change,
        "change_rate": change_rate,
        "direction": direction,
    }