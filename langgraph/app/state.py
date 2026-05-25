from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    question: str
    resolved_question: str
    is_follow_up: bool
    reset_context: bool
    context_strategy: Dict[str, Any]
    inherited_context: Dict[str, Any]

    used_memory_only: bool
    memory_answer_source: str

    session_id: str
    memory: Dict[str, Any]

    aggregation_plan: Dict[str, Any]
    aggregation_result: Dict[str, Any]
    structured_insight: Dict[str, Any]
    follow_up_suggestions: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    query_plans: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    compile_errors: List[Dict[str, Any]]
    request_id: str
    answer: str
    error: Optional[str]
    trace: Dict[str, Any]
    trace_file: str
