from app.semantic.metrics import METRICS


def resolve_metric(metric_name: str) -> dict:
    metric_def = METRICS.get(metric_name)

    if not metric_def:
        raise ValueError(f"Unknown metric: {metric_name}")

    return metric_def