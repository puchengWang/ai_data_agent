from pathlib import Path


TEMPLATE_DIR = Path("app/summary/templates")


def load_summary_template(aggregation_type: str) -> str:
    template_path = TEMPLATE_DIR / f"{aggregation_type}.txt"

    if not template_path.exists():
        template_path = TEMPLATE_DIR / "normal.txt"

    return template_path.read_text(encoding="utf-8")