def build_measure(metric_def: dict) -> str:
    aggregation = metric_def.get("aggregation")
    field = metric_def.get("field")
    measure = metric_def.get("measure")

    if measure:
        return measure

    if not aggregation or not field:
        raise ValueError("Metric must define either measure or aggregation + field")

    aggregation = aggregation.lower()

    if aggregation == "count":
        return f"COUNT({field})"

    if aggregation == "sum":
        return f"SUM({field})"

    if aggregation == "avg":
        return f"AVG({field})"

    if aggregation == "min":
        return f"MIN({field})"

    if aggregation == "max":
        return f"MAX({field})"

    if aggregation == "distinct_count":
        return f"COUNT(DISTINCT {field})"

    raise ValueError(f"Unsupported aggregation: {aggregation}")