def calculate_change(current_value, previous_value):

    if previous_value == 0:
        return {
            "change": None,
            "change_rate": None
        }

    change = current_value - previous_value

    change_rate = (change / previous_value) * 100

    return {
        "change": change,
        "change_rate": round(change_rate, 2)
    }