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

    # -----------------------------------------------------
    # 输入结构
    # -----------------------------------------------------
    #
    # {
    #   "intent": "count_users_by_atime",
    #   "params": {
    #       "start_time": "2026-05-19",
    #       "end_time": "2026-05-20"
    #   },
    #   "request_id": "test-001"
    # }
    #
    # -----------------------------------------------------

    intent = event.get("intent")
    params = event.get("params", {})
    request_id = event.get("request_id")

    # =====================================================
    # 当前仅支持固定 Intent
    # =====================================================
    if intent != "count_users_by_atime":

        return build_response(
            success=False,
            intent=intent,
            request_id=request_id,
            error=f"Unsupported intent: {intent}",
            meta={
                "source": "aurora_mysql",
                "database": DB_NAME,
                "table": "users"
            }
        )

    # =====================================================
    # 参数读取
    # =====================================================
    start_time = params.get("start_time")
    end_time = params.get("end_time")

    if not start_time or not end_time:

        return build_response(
            success=False,
            intent=intent,
            request_id=request_id,
            error="Missing required params: start_time, end_time",
            meta={
                "source": "aurora_mysql",
                "database": DB_NAME,
                "table": "users"
            }
        )

    # =====================================================
    # 固定 SQL
    # =====================================================
    sql = """
        SELECT COUNT(rid) AS count
        FROM users
        WHERE atime > %s
          AND atime < %s
    """

    try:

        # =================================================
        # 连接数据库
        # =================================================
        conn = get_connection()

        with conn.cursor() as cursor:

            cursor.execute(sql, (start_time, end_time))

            result = cursor.fetchone()

        conn.close()

        # =================================================
        # 返回成功结果
        # =================================================
        return build_response(
            success=True,
            intent=intent,
            request_id=request_id,
            data={
                "count": result["count"]
            },
            sql=sql.strip(),
            error=None,
            meta={
                "source": "aurora_mysql",
                "database": DB_NAME,
                "table": "users"
            }
        )

    except Exception as e:

        # =================================================
        # 返回异常结果
        # =================================================
        return build_response(
            success=False,
            intent=intent,
            request_id=request_id,
            data=None,
            sql=sql.strip(),
            error=str(e),
            meta={
                "source": "aurora_mysql",
                "database": DB_NAME,
                "table": "users"
            }
        )