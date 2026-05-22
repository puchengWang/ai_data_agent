from app.semantic.semantic_loader import load_tables


def resolve_dimension_from_question(
    question: str,
    metric_def: dict,
) -> str | None:
    tables = load_tables()

    table_name = metric_def["table"]
    table_def = tables.get(table_name)

    if not table_def:
        return None

    allowed_dimensions = metric_def.get("dimensions", [])

    fields = table_def.get("fields", {})

    for field_name in allowed_dimensions:
        field_def = fields.get(field_name, {})

        candidates = [
            field_name,
            field_def.get("business_name", ""),
            field_def.get("description", ""),
            *field_def.get("aliases", []),
        ]

        for candidate in candidates:
            if candidate and candidate in question:
                return field_name

    return None