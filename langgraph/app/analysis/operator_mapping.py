AGGREGATION_OPERATOR_MAPPING = {
    "normal": [],

    "compare": [
        "growth_rate",
    ],

    "trend": [
        "peak_valley",
        "volatility",
        "basic_anomaly",
    ],

    "group_by": [
        "contribution",
    ],

    "top_n": [
        "contribution",
    ],

    "distribution": [
        "contribution",
    ],

    "compare_by_dimension": [
        "growth_rate",
    ],

    "trend_by_dimension": [
        "peak_valley",
        "volatility",
        "basic_anomaly",
    ],
}


def get_operators_for_aggregation(aggregation_type: str) -> list[str]:
    return AGGREGATION_OPERATOR_MAPPING.get(aggregation_type, [])