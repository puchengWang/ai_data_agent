from typing import Any, Dict, List, Optional


def build_task(
    task_id: str,
    task_name: str,
    metric: str,
    params: Dict[str, Any],
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "task_id": task_id,
        "task_name": task_name,
        "metric": metric,
        "params": params,
        "filters": filters or [],
    }


def build_query_plan(
    task_id: str,
    task_name: str,
    metric: str,
    business_name: str,
    engine: str,
    datasource: str,
    sql: str,
    params: List[Any],
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "protocol_version": "1.0",
        "task_id": task_id,
        "task_name": task_name,
        "metric": metric,
        "business_name": business_name,
        "engine": engine,
        "datasource": datasource,
        "query_type": "sql",
        "sql": sql,
        "params": params,
        "meta": meta or {},
    }


def build_tool_result(
    task_id: str,
    task_name: str,
    success: bool,
    data: Optional[Dict[str, Any]],
    error: Optional[str],
    query_plan: Dict[str, Any],
    latency_ms: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "protocol_version": "1.0",
        "task_id": task_id,
        "task_name": task_name,
        "success": success,
        "data": data,
        "error": error,
        "latency_ms": latency_ms,
        "query_plan": query_plan,
    }