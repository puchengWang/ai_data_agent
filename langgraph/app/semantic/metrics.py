METRICS = {
    "user_count": {
        "business_name": "用户数量",
        "description": "统计 users 表中的用户数量",
        "table": "users",
        "measure": "COUNT(rid)",
        "time_field": "atime",
        "default_grain": "day",
        "dimensions": [],
        "filters": [],
        "meta": {
            "source": "aurora_mysql",
            "database": "user",
            "table": "users"
        }
    }
}