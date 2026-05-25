import threading
import time
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

import app.graph as graph_module
import app.memory.context_strategy as context_strategy_module
from app.runtime.bedrock_mock import mock_bedrock_calls


app = FastAPI(
    title="AI Data Agent Runtime API",
    version="0.1.0",
)

GRAPH_INVOKE_LOCK = threading.Lock()


class AnalyzeRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str = "default-session"
    request_id: Optional[str] = None
    mock_bedrock: bool = False
    debug: bool = False


class AnalyzeResponse(BaseModel):
    success: bool
    runtime_mode: str
    session_id: str
    request_id: str
    answer: Optional[str] = None
    structured_insight: Optional[Dict[str, Any]] = None
    follow_up_suggestions: list[Dict[str, Any]] = []
    trace_file: Optional[str] = None
    aggregation_type: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    debug: Optional[Dict[str, Any]] = None


@app.get("/health")
def health() -> Dict[str, str]:
    return {
        "status": "ok",
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    request_id = request.request_id or f"api-{int(time.time())}"
    runtime_mode = "mock_bedrock" if request.mock_bedrock else "real_bedrock"

    try:
        with GRAPH_INVOKE_LOCK:
            if request.mock_bedrock:
                with mock_bedrock_calls(
                    graph_module=graph_module,
                    context_strategy_module=context_strategy_module,
                ):
                    result = _invoke_graph(request, request_id)
            else:
                result = _invoke_graph(request, request_id)

        return _build_success_response(
            result=result,
            runtime_mode=runtime_mode,
            session_id=request.session_id,
            request_id=request_id,
            include_debug=request.debug,
        )

    except Exception as e:
        return AnalyzeResponse(
            success=False,
            runtime_mode=runtime_mode,
            session_id=request.session_id,
            request_id=request_id,
            error={
                "type": e.__class__.__name__,
                "message": str(e),
            },
        )


def _invoke_graph(
    request: AnalyzeRequest,
    request_id: str,
) -> Dict[str, Any]:
    graph = graph_module.build_graph()

    return graph.invoke({
        "session_id": request.session_id,
        "question": request.question,
        "request_id": request_id,
    })


def _build_success_response(
    result: Dict[str, Any],
    runtime_mode: str,
    session_id: str,
    request_id: str,
    include_debug: bool,
) -> AnalyzeResponse:
    aggregation_plan = result.get("aggregation_plan") or {}

    debug_payload = None
    if include_debug:
        trace = result.get("trace") or {}
        debug_payload = {
            "steps": [
                step.get("step")
                for step in trace.get("steps", [])
            ],
            "query_plans": result.get("query_plans"),
            "tool_results": result.get("tool_results"),
            "aggregation_result": result.get("aggregation_result"),
        }

    return AnalyzeResponse(
        success=True,
        runtime_mode=runtime_mode,
        session_id=session_id,
        request_id=request_id,
        answer=result.get("answer"),
        structured_insight=result.get("structured_insight"),
        follow_up_suggestions=result.get("follow_up_suggestions") or [],
        trace_file=result.get("trace_file"),
        aggregation_type=aggregation_plan.get("aggregation_type"),
        debug=debug_payload,
    )
