from app.protocols.query_protocol import build_query_plan


def compile_metric_query(task: dict, metric_def: dict) -> dict:
    task_id = task["task_id"]
    task_name = task["task_name"]
    metric_name = task["metric"]
    params = task.get("params", {})

    table = metric_def["table"]
    measure = metric_def["measure"]
    time_field = metric_def.get("time_field")

    sql = f"""
        SELECT {measure} AS value
        FROM {table}
    """

    sql_params = []
    conditions = []

    if time_field:
        start_time = params.get("start_time")
        end_time = params.get("end_time")

        if start_time and end_time:
            conditions.append(f"{time_field} >= %s")
            conditions.append(f"{time_field} < %s")
            sql_params.extend([start_time, end_time])

        elif end_time:
            conditions.append(f"{time_field} < %s")
            sql_params.append(end_time)

        elif start_time:
            conditions.append(f"{time_field} >= %s")
            sql_params.append(start_time)

    if conditions:
        sql += "\nWHERE " + "\n  AND ".join(conditions)

    meta = metric_def.get("meta", {})

    return build_query_plan(
        task_id=task_id,
        task_name=task_name,
        metric=metric_name,
        business_name=metric_def["business_name"],
        engine=meta.get("engine", "aurora_mysql"),
        datasource=meta.get("datasource", "user"),
        sql=sql.strip(),
        params=sql_params,
        meta=meta,
    )