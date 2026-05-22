from typing import Dict, Any


def infer_semantic_type(column: Dict[str, Any]) -> str:
    name = column["name"].lower()
    comment = column.get("comment", "")

    if name in ["id", "rid", "user_id", "uid"]:
        return "identifier"

    if name in ["ctime", "created_at", "create_time", "register_time"]:
        return "event_time"

    if name in ["atime", "active_time", "last_active_time"]:
        return "activity_time"

    if name in ["country", "region", "province", "city"]:
        return "geography"

    if name in ["status", "type", "level", "channel", "source"]:
        return "dimension"

    if any(word in name for word in ["phone", "email", "name", "address"]):
        return "pii"

    if "time" in name or name.endswith("_at"):
        return "time"

    return "attribute"


def infer_business_name(column: Dict[str, Any]) -> str:
    if column.get("comment"):
        return column["comment"]

    return column["name"]


def infer_default_time_field(columns):
    priority = ["ctime", "created_at", "create_time", "register_time", "atime"]

    column_names = {col["name"] for col in columns}

    for field in priority:
        if field in column_names:
            return field

    return None


def infer_metric_seed(table_name: str, primary_key: str, table_comment: str):
    if not primary_key:
        return None

    return {
        f"{table_name}_count": {
            "business_name": f"{table_comment or table_name}数量",
            "description": f"统计 {table_comment or table_name} 的数量",
            "table": table_name,
            "measure": f"COUNT({primary_key})",
            "time_field": None,
            "metric_type": "count",
            "dimensions": [],
            "filters": [],
            "meta": {
                "engine": "aurora_mysql",
                "datasource": "user",
                "database": "user",
                "table": table_name,
            }
        }
    }