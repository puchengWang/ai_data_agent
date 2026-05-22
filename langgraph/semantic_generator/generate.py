import argparse
from pathlib import Path

from semantic_generator.ddl_parser import parse_ddl
from semantic_generator.yaml_generator import (
    generate_tables_yaml,
    generate_metrics_yaml,
    generate_glossary_yaml,
    write_yaml,
)


def main():
    parser = argparse.ArgumentParser(
        description="Generate semantic YAML configs from MySQL DDL"
    )

    parser.add_argument(
        "--ddl",
        required=True,
        help="Path to MySQL DDL file"
    )

    parser.add_argument(
        "--output-dir",
        default="semantic_configs",
        help="Output directory for generated YAML files"
    )

    args = parser.parse_args()

    ddl_text = Path(args.ddl).read_text(encoding="utf-8")

    parsed = parse_ddl(ddl_text)

    output_dir = Path(args.output_dir)

    tables_yaml = generate_tables_yaml(parsed)
    metrics_yaml = generate_metrics_yaml(parsed)
    glossary_yaml = generate_glossary_yaml(parsed)

    write_yaml(tables_yaml, output_dir / "tables.yaml")
    write_yaml(metrics_yaml, output_dir / "metrics.yaml")
    write_yaml(glossary_yaml, output_dir / "glossary.yaml")

    print(f"Generated semantic configs to: {output_dir}")


if __name__ == "__main__":
    main()