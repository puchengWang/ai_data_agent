import yaml
from pathlib import Path
from typing import Dict, Any

from semantic_generator.semantic_inference import (
    infer_semantic_type,
    infer_business_name,
    infer_default_time_field,
    infer_metric_seed,
)


def generate_tables_yaml(parsed: Dict[str, Any]) -> Dict[str, Any]:
    table_name = parsed["table_name"]
    table_comment = parsed["table_comment"]
    columns = parsed["columns"]
    primary_key = parsed["primary_key"]

    fields = {}

    for col in columns:
        fields[col["name"]] = {
            "business_name": infer_business_name(col),
            "type": col["type"],
            "description": col.get("comment", ""),
            "semantic_type": infer_semantic_type(col),
        }

    return {
        "tables": {
            table_name: {
                "datasource": "aurora_mysql",
                "database": "user",
                "physical_table": table_name,
                "business_name": table_comment or table_name,
                "description": table_comment or "",
                "primary_key": primary_key,
                "default_time_field": infer_default_time_field(columns),
                "owner": "data_team",
                "tags": [
                    table_name
                ],
                "fields": fields,
            }
        }
    }


def generate_metrics_yaml(parsed: Dict[str, Any]) -> Dict[str, Any]:
    metric_seed = infer_metric_seed(
        table_name=parsed["table_name"],
        primary_key=parsed["primary_key"],
        table_comment=parsed["table_comment"],
    )

    return {
        "metrics": metric_seed or {}
    }


def generate_glossary_yaml(parsed: Dict[str, Any]) -> Dict[str, Any]:
    table_name = parsed["table_name"]
    table_comment = parsed["table_comment"]

    terms = {}

    if table_comment:
        terms[table_comment] = {
            "description": table_comment,
            "tables": [table_name],
            "fields": [],
        }

    for col in parsed["columns"]:
        if col.get("comment"):
            terms[col["comment"]] = {
                "description": col["comment"],
                "tables": [table_name],
                "fields": [col["name"]],
            }

    return {
        "terms": terms
    }


def write_yaml(data: Dict[str, Any], output_path: str):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )