def compile_metric_query(metric_name: str, metric_def: dict, params: dict) -> dict:
    table = metric_def["table"]
    measure = metric_def["measure"]
    time_field = metric_def["time_field"]

    start_time = params["start_time"]
    end_time = params["end_time"]

    sql = f"""
        SELECT {measure} AS value
        FROM {table}
        WHERE {time_field} > %s
          AND {time_field} < %s
    """

    return {
        "metric": metric_name,
        "business_name": metric_def["business_name"],
        "sql": sql.strip(),
        "params": [start_time, end_time],
        "meta": metric_def.get("meta", {})
    }