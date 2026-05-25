from typing import Any, Dict, Optional

from app.analysis.operator_mapping import AGGREGATION_OPERATOR_MAPPING
from app.analysis.operator_registry import OPERATOR_REGISTRY
from app.semantic.semantic_loader import load_metrics, load_tables


DIMENSION_REQUIRED_ANALYSIS_TYPES = {
    "group_by",
    "top_n",
    "distribution",
    "compare_by_dimension",
    "trend_by_dimension",
}


def build_capability_catalog() -> Dict[str, Any]:
    metrics = load_metrics()
    tables = load_tables()

    metric_capabilities = {}

    for metric_name, metric_def in metrics.items():
        table_name = metric_def.get("table")
        table_def = tables.get(table_name, {})
        fields = table_def.get("fields", {})

        dimensions = {}
        for dimension_name in metric_def.get("dimensions", []):
            field_def = fields.get(dimension_name, {})
            dimensions[dimension_name] = {
                "name": dimension_name,
                "business_name": field_def.get("business_name", dimension_name),
                "description": field_def.get("description", ""),
                "semantic_type": field_def.get("semantic_type"),
                "aliases": field_def.get("aliases", []),
            }

        metric_capabilities[metric_name] = {
            "name": metric_name,
            "business_name": metric_def.get("business_name", metric_name),
            "description": metric_def.get("description", ""),
            "table": table_name,
            "time_field": metric_def.get("time_field"),
            "dimensions": dimensions,
        }

    analysis_types = {
        analysis_type: {
            "name": analysis_type,
            "requires_dimension": (
                analysis_type in DIMENSION_REQUIRED_ANALYSIS_TYPES
            ),
            "operators": operators,
        }
        for analysis_type, operators in AGGREGATION_OPERATOR_MAPPING.items()
    }

    return {
        "metrics": metric_capabilities,
        "analysis_types": analysis_types,
        "operators": sorted(OPERATOR_REGISTRY.keys()),
    }


def validate_capability(
    metric: str,
    analysis_type: Optional[str] = None,
    dimension: Optional[str] = None,
    catalog: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    catalog = catalog or build_capability_catalog()
    errors = []

    metric_capability = catalog["metrics"].get(metric)
    if not metric_capability:
        errors.append(f"Unsupported metric: {metric}")

    if analysis_type and analysis_type not in catalog["analysis_types"]:
        errors.append(f"Unsupported analysis_type: {analysis_type}")

    if dimension and metric_capability:
        if dimension not in metric_capability.get("dimensions", {}):
            errors.append(f"Unsupported dimension for {metric}: {dimension}")

    if analysis_type and metric_capability:
        type_capability = catalog["analysis_types"].get(analysis_type, {})
        if type_capability.get("requires_dimension") and not dimension:
            errors.append(f"analysis_type requires dimension: {analysis_type}")

    return {
        "valid": not errors,
        "errors": errors,
    }
