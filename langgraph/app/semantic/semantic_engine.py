from app.semantic.semantic_loader import load_metrics, load_tables, load_glossary


class SemanticRegistry:
    def __init__(self):
        self.metrics = load_metrics()
        self.tables = load_tables()
        self.glossary = load_glossary()

    def resolve_metric(self, metric_name: str) -> dict:
        metric = self.metrics.get(metric_name)

        if not metric:
            raise ValueError(f"Unknown metric: {metric_name}")

        return metric

    def get_table(self, table_name: str) -> dict:
        table = self.tables.get(table_name)

        if not table:
            raise ValueError(f"Unknown table: {table_name}")

        return table


registry = SemanticRegistry()


def resolve_metric(metric_name: str) -> dict:
    return registry.resolve_metric(metric_name)