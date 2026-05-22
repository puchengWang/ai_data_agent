from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    question: str
    aggregation_plan: Dict[str, Any]
    aggregation_result: Dict[str, Any]
    tasks: List[Dict[str, Any]]
    query_plans: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    compile_errors: List[Dict[str, Any]]
    request_id: str
    answer: str
    error: Optional[str]
    trace: Dict[str, Any]
    trace_file: str