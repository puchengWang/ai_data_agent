import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_CONFIG_DIR = PROJECT_ROOT / "semantic_configs"

METRICS_FILE = SEMANTIC_CONFIG_DIR / "metrics.yaml"
TABLES_FILE = SEMANTIC_CONFIG_DIR / "tables.yaml"
GLOSSARY_FILE = SEMANTIC_CONFIG_DIR / "glossary.yaml"

SUPPORTED_AGGREGATIONS = {
    "count",
    "sum",
    "avg",
    "min",
    "max",
    "distinct_count",
}


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing semantic config file: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def add_error(errors: List[str], message: str):
    errors.append(f"[ERROR] {message}")


def add_warning(warnings: List[str], message: str):
    warnings.append(f"[WARN] {message}")


def validate_metrics(metrics: Dict[str, Any], tables: Dict[str, Any]):
    errors = []
    warnings = []

    required_metric_fields = [
        "business_name",
        "table",
        "aggregation",
        "field",
        "time_field",
        "metric_type",
        "dimensions",
        "filters",
        "meta",
    ]

    for metric_name, metric_def in metrics.items():
        prefix = f"metric '{metric_name}'"

        for field in required_metric_fields:
            if field not in metric_def:
                add_error(errors, f"{prefix} missing required field: {field}")

        table_name = metric_def.get("table")

        if not table_name:
            continue

        table_def = tables.get(table_name)

        if not table_def:
            add_error(errors, f"{prefix} references unknown table: {table_name}")
            continue

        table_fields = table_def.get("fields", {})

        metric_field = metric_def.get("field")

        if metric_field and metric_field not in table_fields:
            add_error(
                errors,
                f"{prefix} references unknown field '{metric_field}' in table '{table_name}'"
            )

        time_field = metric_def.get("time_field")

        if time_field and time_field not in table_fields:
            add_error(
                errors,
                f"{prefix} references unknown time_field '{time_field}' in table '{table_name}'"
            )

        aggregation = metric_def.get("aggregation")

        if aggregation and aggregation not in SUPPORTED_AGGREGATIONS:
            add_error(
                errors,
                f"{prefix} has unsupported aggregation: {aggregation}"
            )

        dimensions = metric_def.get("dimensions", [])

        if dimensions is None:
            add_error(errors, f"{prefix} dimensions must be a list")
            dimensions = []

        if not isinstance(dimensions, list):
            add_error(errors, f"{prefix} dimensions must be a list")
            dimensions = []

        for dimension in dimensions:
            field_def = table_fields.get(dimension)

            if not field_def:
                add_error(
                    errors,
                    f"{prefix} references unknown dimension '{dimension}' in table '{table_name}'"
                )
                continue

            semantic_type = field_def.get("semantic_type")

            if semantic_type != "dimension":
                add_warning(
                    warnings,
                    f"{prefix} dimension '{dimension}' semantic_type is '{semantic_type}', expected 'dimension'"
                )

        meta = metric_def.get("meta", {})

        if meta:
            if not meta.get("engine"):
                add_warning(warnings, f"{prefix} meta.engine is missing")

            if not meta.get("datasource"):
                add_warning(warnings, f"{prefix} meta.datasource is missing")

            if not meta.get("database"):
                add_warning(warnings, f"{prefix} meta.database is missing")

            if not meta.get("table"):
                add_warning(warnings, f"{prefix} meta.table is missing")

        measure = metric_def.get("measure")

        if measure:
            add_warning(
                warnings,
                f"{prefix} defines explicit measure '{measure}'. Ensure it matches aggregation + field."
            )

    return errors, warnings


def validate_tables(tables: Dict[str, Any]):
    errors = []
    warnings = []

    required_table_fields = [
        "datasource",
        "database",
        "physical_table",
        "business_name",
        "primary_key",
        "fields",
    ]

    required_field_fields = [
        "business_name",
        "type",
        "description",
        "semantic_type",
    ]

    for table_name, table_def in tables.items():
        prefix = f"table '{table_name}'"

        for field in required_table_fields:
            if field not in table_def:
                add_error(errors, f"{prefix} missing required field: {field}")

        fields = table_def.get("fields", {})

        if not fields:
            add_error(errors, f"{prefix} has no fields")
            continue

        primary_key = table_def.get("primary_key")

        if primary_key and primary_key not in fields:
            add_error(
                errors,
                f"{prefix} primary_key '{primary_key}' not found in fields"
            )

        default_time_field = table_def.get("default_time_field")

        if default_time_field and default_time_field not in fields:
            add_error(
                errors,
                f"{prefix} default_time_field '{default_time_field}' not found in fields"
            )

        for field_name, field_def in fields.items():
            field_prefix = f"{prefix}.field '{field_name}'"

            for required in required_field_fields:
                if required not in field_def:
                    add_error(errors, f"{field_prefix} missing required field: {required}")

            if not field_def.get("business_name"):
                add_warning(warnings, f"{field_prefix} business_name is empty")

            if not field_def.get("description"):
                add_warning(warnings, f"{field_prefix} description is empty")

            semantic_type = field_def.get("semantic_type")

            if semantic_type not in {
                "identifier",
                "dimension",
                "event_time",
                "activity_time",
                "time",
                "attribute",
                "measure",
                "geography",
                "pii",
            }:
                add_warning(
                    warnings,
                    f"{field_prefix} has uncommon semantic_type: {semantic_type}"
                )

    return errors, warnings


def validate_glossary(glossary: Dict[str, Any], tables: Dict[str, Any]):
    errors = []
    warnings = []

    for term, term_def in glossary.items():
        prefix = f"term '{term}'"

        referenced_tables = term_def.get("tables", [])
        referenced_fields = term_def.get("fields", [])

        if not referenced_tables:
            add_warning(warnings, f"{prefix} has no referenced tables")

        for table_name in referenced_tables:
            if table_name not in tables:
                add_error(
                    errors,
                    f"{prefix} references unknown table: {table_name}"
                )

        for field_name in referenced_fields:
            found = False

            for table_name in referenced_tables:
                table_def = tables.get(table_name, {})
                fields = table_def.get("fields", {})

                if field_name in fields:
                    found = True
                    break

            if not found:
                add_warning(
                    warnings,
                    f"{prefix} references field '{field_name}' but it was not found in referenced tables"
                )

    return errors, warnings


def main():
    metrics_data = load_yaml(METRICS_FILE)
    tables_data = load_yaml(TABLES_FILE)

    glossary_data = {}
    if GLOSSARY_FILE.exists():
        glossary_data = load_yaml(GLOSSARY_FILE)

    metrics = metrics_data.get("metrics", {})
    tables = tables_data.get("tables", {})
    glossary = glossary_data.get("terms", {})

    all_errors = []
    all_warnings = []

    table_errors, table_warnings = validate_tables(tables)
    metric_errors, metric_warnings = validate_metrics(metrics, tables)
    glossary_errors, glossary_warnings = validate_glossary(glossary, tables)

    all_errors.extend(table_errors)
    all_errors.extend(metric_errors)
    all_errors.extend(glossary_errors)

    all_warnings.extend(table_warnings)
    all_warnings.extend(metric_warnings)
    all_warnings.extend(glossary_warnings)

    print("\nSemantic Config Validation Result")
    print("=" * 40)

    if all_errors:
        print("\nErrors:")
        for error in all_errors:
            print(error)

    if all_warnings:
        print("\nWarnings:")
        for warning in all_warnings:
            print(warning)

    if not all_errors and not all_warnings:
        print("\nOK: No errors or warnings found.")

    print("\nSummary:")
    print(f"errors: {len(all_errors)}")
    print(f"warnings: {len(all_warnings)}")

    if all_errors:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()