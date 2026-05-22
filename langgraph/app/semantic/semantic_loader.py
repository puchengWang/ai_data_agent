import yaml
from pathlib import Path


SEMANTIC_CONFIG_DIR = Path("semantic_configs")


def load_yaml(file_name: str) -> dict:
    path = SEMANTIC_CONFIG_DIR / file_name

    if not path.exists():
        raise FileNotFoundError(f"Semantic config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_metrics() -> dict:
    data = load_yaml("metrics.yaml")
    return data.get("metrics", {})


def load_tables() -> dict:
    data = load_yaml("tables.yaml")
    return data.get("tables", {})


def load_glossary() -> dict:
    data = load_yaml("glossary.yaml")
    return data.get("terms", {})