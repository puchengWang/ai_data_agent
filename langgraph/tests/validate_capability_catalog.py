import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.capabilities.catalog import (  # noqa: E402
    build_capability_catalog,
    validate_capability,
)


EXPECTED_ANALYSIS_TYPES = {
    "normal",
    "compare",
    "trend",
    "group_by",
    "top_n",
    "distribution",
    "compare_by_dimension",
    "trend_by_dimension",
}

UNSUPPORTED_DIMENSIONS = {
    "channel",
    "region",
    "device",
}


def add_error(errors: list[str], message: str) -> None:
    errors.append(f"[ERROR] {message}")


def main() -> None:
    catalog = build_capability_catalog()
    errors = []

    metrics = catalog.get("metrics", {})
    analysis_types = catalog.get("analysis_types", {})
    operators = catalog.get("operators", [])

    if "user_count" not in metrics:
        add_error(errors, "Expected metric is missing: user_count")

    user_count = metrics.get("user_count", {})
    dimensions = user_count.get("dimensions", {})

    if set(dimensions.keys()) != {"level"}:
        add_error(
            errors,
            f"Expected only user_count dimension 'level', got: {sorted(dimensions.keys())}",
        )

    missing_analysis_types = EXPECTED_ANALYSIS_TYPES - set(analysis_types.keys())
    if missing_analysis_types:
        add_error(
            errors,
            f"Missing analysis types: {sorted(missing_analysis_types)}",
        )

    valid_level = validate_capability(
        metric="user_count",
        analysis_type="group_by",
        dimension="level",
        catalog=catalog,
    )
    if not valid_level["valid"]:
        add_error(errors, f"Expected level to be valid: {valid_level['errors']}")

    missing_dimension = validate_capability(
        metric="user_count",
        analysis_type="group_by",
        catalog=catalog,
    )
    if missing_dimension["valid"]:
        add_error(errors, "Expected group_by without dimension to be invalid")

    unsupported_metric = validate_capability(
        metric="revenue",
        analysis_type="normal",
        catalog=catalog,
    )
    if unsupported_metric["valid"]:
        add_error(errors, "Expected unsupported metric to be invalid: revenue")

    for dimension in UNSUPPORTED_DIMENSIONS:
        result = validate_capability(
            metric="user_count",
            analysis_type="group_by",
            dimension=dimension,
            catalog=catalog,
        )
        if result["valid"]:
            add_error(
                errors,
                f"Expected unsupported dimension to be invalid: {dimension}",
            )

    print("\nCapability Catalog Validation Result")
    print("=" * 40)
    print(f"metrics: {sorted(metrics.keys())}")
    print(f"user_count dimensions: {sorted(dimensions.keys())}")
    print(f"analysis_types: {sorted(analysis_types.keys())}")
    print(f"operators: {operators}")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(error)

    print("\nSummary:")
    print(f"errors: {len(errors)}")

    if errors:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
