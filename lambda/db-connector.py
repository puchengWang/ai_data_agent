import json
import pymysql


# =========================================================
# Aurora MySQL Config (MVP阶段先固定写在代码中)
# bedrock : readonly 权限
# =========================================================
DB_HOST = "rds-user-aurora-cluster.cluster-ro-c1rmcdqnulkf.ap-southeast-1.rds.amazonaws.com"
DB_PORT = 3306
DB_USER = "bedrock"
DB_PASSWORD = "lwYINjj3R3PZcZIX"
DB_NAME = "user"


# =========================================================
# 获取数据库连接
# =========================================================
def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
        cursorclass=pymysql.cursors.DictCursor,
    )


# =========================================================
# 标准返回结构
# =========================================================
def build_response(
    success,
    intent,
    data=None,
    sql=None,
    error=None,
    meta=None,
    request_id=None
):
    return {
        "success": success,
        "intent": intent,
        "request_id": request_id,
        "data": data,
        "sql": sql,
        "error": error,
        "meta": meta
    }


# =========================================================
# Lambda 主入口
# =========================================================
def lambda_handler(event, context):
    request_id = event.get("request_id")
    query_plan = event.get("query_plan")

    if not query_plan:
        return build_response(
            success=False,
            intent=None,
            request_id=request_id,
            error="Missing query_plan"
        )

    sql = query_plan.get("sql")
    sql_params = query_plan.get("params", [])
    metric = query_plan.get("metric")

    if not sql:
        return build_response(
            success=False,
            intent=metric,
            request_id=request_id,
            error="Missing sql in query_plan"
        )

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(sql, sql_params)
            result = cursor.fetchone()

        conn.close()

        return {
            "success": True,
            "metric": metric,
            "request_id": request_id,
            "data": {
                "value": result["value"]
            },
            "sql": sql,
            "params": sql_params,
            "error": None,
            "meta": query_plan.get("meta", {})
        }

    except Exception as e:
        return {
            "protocol_version": "1.0",
            "success": False,
            "task_id": query_plan.get("task_id"),
            "task_name": query_plan.get("task_name"),
            "metric": metric,
            "request_id": request_id,
            "data": None,
            "sql": sql,
            "params": sql_params,
            "error": str(e),
            "meta": query_plan.get("meta", {})
        }