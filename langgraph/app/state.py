from typing import Any, Dict, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    question: str
    metric: str
    metric_def: Dict[str, Any]
    params: Dict[str, Any]
    query_plan: Dict[str, Any]
    request_id: str
    tool_result: Dict[str, Any]
    answer: str
    error: Optional[str]