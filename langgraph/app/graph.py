from langgraph.graph import StateGraph, END
from app.observability.tracer import now_ms, write_trace
from app.protocols.query_protocol import build_tool_result
from app.planner.aggregation_planner import build_aggregation_plan
# from app.planner.comparison_engine import calculate_change
from app.analysis.operator_registry import OPERATOR_REGISTRY

from app.memory.session_store import (
    default_session_data,
    load_session,
    save_session,
)
from app.memory.context_resolver import resolve_question_with_context

from app.summary.summary_template_loader import load_summary_template
from app.analysis.operator_executor import execute_analysis_operators
from app.insight.structured_insight import build_structured_insight
from app.follow_up.suggestion_generator import generate_follow_up_suggestions

from app.state import AgentState
from app.llm.bedrock_client import invoke_bedrock_json, invoke_bedrock_text
from app.semantic.semantic_engine import resolve_metric
from app.semantic.query_compiler import compile_metric_query
from app.tools.lambda_sql_tool import invoke_sql_executor_with_query_plan




def can_answer_from_memory(state: AgentState) -> bool:
    if not state.get("is_follow_up"):
        return False

    inherited_context = state.get("inherited_context") or {}

    last_analysis = inherited_context.get("last_analysis")

    if not last_analysis:
        return False

    question = state.get("question", "")

    memory_answer_keywords = [
        "哪个",
        "哪一个",
        "下降最多",
        "增长最多",
        "最高",
        "最低",
        "最多",
        "最少",
    ]

    return any(keyword in question for keyword in memory_answer_keywords)


def answer_from_memory_node(state: AgentState) -> AgentState:
    inherited_context = state.get("inherited_context", {})
    last_analysis = inherited_context.get("last_analysis")

    prompt = f"""
你是一个企业数据分析助手。

用户当前问题：
{state["question"]}

这是上一轮已经完成的结构化分析结果：
{last_analysis}

请只基于上一轮分析结果回答当前问题。
不要重新假设数据，不要生成新的查询。
如果上一轮结果不足以回答，请明确说明。
"""

    answer = invoke_bedrock_text(prompt)

    return {
        **state,
        "answer": answer,
        "used_memory_only": True,
        "memory_answer_source": "last_analysis",
    }


def get_context_for_resolution(session_data: dict) -> dict:
    return (
        session_data.get("last_analysis_context")
        or session_data.get("last_context")
        or {}
    )


def load_memory_node(state: AgentState) -> AgentState:
    session_id = state.get("session_id", "default-session")
    session_data = load_session(session_id)
    context_for_resolution = get_context_for_resolution(session_data)

    resolved = resolve_question_with_context(
        question=state["question"],
        last_context=context_for_resolution,
    )

    inherited_context = resolved.get("inherited_context") or {}

    return {
        **state,
        "session_id": session_id,
        "memory": session_data,
        "resolved_question": resolved.get("resolved_question", state["question"]),
        "is_follow_up": resolved.get("is_follow_up", False),
        "reset_context": resolved.get("reset_context", False),
        "context_strategy": resolved.get("context_strategy", {}),
        "inherited_context": inherited_context,
    }


def build_analysis_context(state: AgentState) -> dict:
    aggregation_plan = state.get("aggregation_plan", {})

    context = {
        "question": state.get("question"),
        "resolved_question": state.get("resolved_question"),
        "aggregation_type": aggregation_plan.get("aggregation_type"),
        "metric": None,
        "dimension": aggregation_plan.get("dimension"),
        "params": None,
        "tasks": state.get("tasks"),
        "query_plans": state.get("query_plans"),
        "aggregation_result": state.get("aggregation_result"),
        "structured_insight": state.get("structured_insight"),
        "follow_up_suggestions": state.get("follow_up_suggestions"),
        "answer": state.get("answer"),
    }

    tasks = state.get("tasks", [])
    if tasks:
        context["metric"] = tasks[0].get("metric")
        context["params"] = tasks[0].get("params")

    return context


def build_answer_context(state: AgentState) -> dict:
    return {
        "question": state.get("question"),
        "resolved_question": state.get("resolved_question"),
        "answer": state.get("answer"),
        "used_memory_only": state.get("used_memory_only", False),
        "memory_answer_source": state.get("memory_answer_source"),
        "trace_file": state.get("trace_file"),
    }

def aggregation_analysis_node(state: AgentState) -> AgentState:
    aggregation_plan = state.get("aggregation_plan", {})
    aggregation_type = aggregation_plan.get("aggregation_type")

    aggregation_result = {
        "aggregation_type": aggregation_type,
        "analysis": None,
        "operator_results": {},
        "error": None,
    }

    try:
        analysis_input = build_analysis_input(
            aggregation_type=aggregation_type,
            aggregation_plan=aggregation_plan,
            tool_results=state.get("tool_results", []),
        )

        operator_results = execute_analysis_operators(
            aggregation_type=aggregation_type,
            analysis_input=analysis_input,
        )

        aggregation_result["analysis"] = analysis_input
        aggregation_result["operator_results"] = operator_results

    except Exception as e:
        aggregation_result["error"] = str(e)

    trace = state.get("trace", {})
    steps = trace.get("steps", [])

    steps.append({
        "step": "aggregation_analysis",
        "status": "success" if not aggregation_result.get("error") else "partial_success",
        "output": aggregation_result,
        "timestamp_ms": now_ms(),
    })

    trace["steps"] = steps

    return {
        **state,
        "aggregation_result": aggregation_result,
        "trace": trace,
    }


def structured_insight_node(state: AgentState) -> AgentState:
    structured_insight = build_structured_insight(
        question=state.get("question", ""),
        aggregation_plan=state.get("aggregation_plan", {}),
        aggregation_result=state.get("aggregation_result", {}),
        tool_results=state.get("tool_results", []),
    )

    trace = state.get("trace", {})
    steps = trace.get("steps", [])

    steps.append({
        "step": "structured_insight",
        "status": "success",
        "output": structured_insight,
        "timestamp_ms": now_ms(),
    })

    trace["steps"] = steps

    return {
        **state,
        "structured_insight": structured_insight,
        "trace": trace,
    }


def follow_up_suggestions_node(state: AgentState) -> AgentState:
    suggestions = generate_follow_up_suggestions(
        structured_insight=state.get("structured_insight", {}),
    )

    trace = state.get("trace", {})
    steps = trace.get("steps", [])

    steps.append({
        "step": "follow_up_suggestions",
        "status": "success",
        "output": suggestions,
        "timestamp_ms": now_ms(),
    })

    trace["steps"] = steps

    return {
        **state,
        "follow_up_suggestions": suggestions,
        "trace": trace,
    }


def build_analysis_input(
    aggregation_type: str,
    aggregation_plan: dict,
    tool_results: list,
) -> dict:

    if aggregation_type == "normal":
        return {
            "tool_results": tool_results,
        }

    if aggregation_type == "compare":
        results_by_task_id = {
            item["task_id"]: item
            for item in tool_results
        }

        current_result = results_by_task_id.get("current_period")
        previous_result = results_by_task_id.get("previous_period")

        if not current_result or not previous_result:
            raise ValueError("Missing current_period or previous_period result")

        if not current_result.get("success") or not previous_result.get("success"):
            raise ValueError("Current or previous period query failed")

        return {
            "current_value": current_result["data"]["value"],
            "previous_value": previous_result["data"]["value"],
        }

    if aggregation_type in ["group_by", "top_n", "distribution"]:
        rows = []

        for item in tool_results:
            if item.get("success"):
                rows.extend(item.get("data", {}).get("rows", []))

        if not rows:
            raise ValueError(f"No valid {aggregation_type} data")

        return {
            "dimension": aggregation_plan.get("dimension"),
            "rows": rows,
        }

    if aggregation_type == "trend":
        time_series = []

        for item in tool_results:
            query_plan = item.get("query_plan", {})
            params = query_plan.get("params", [])

            time_label = params[0] if params else None

            value = None
            if item.get("success"):
                value = item.get("data", {}).get("value")

            time_series.append({
                "time_label": time_label,
                "task_id": item.get("task_id"),
                "task_name": item.get("task_name"),
                "value": value,
                "success": item.get("success"),
                "error": item.get("error"),
            })

        valid_values = [
            item["value"]
            for item in time_series
            if item.get("value") is not None
        ]

        if not valid_values:
            raise ValueError("No valid trend data")

        return {
            "grain": aggregation_plan.get("grain", "day"),
            "time_series": time_series,
            "summary_stats": {
                "points": len(valid_values),
                "min": min(valid_values),
                "max": max(valid_values),
                "start_value": valid_values[0],
                "end_value": valid_values[-1],
                "change": valid_values[-1] - valid_values[0],
            },
        }

    if aggregation_type == "compare_by_dimension":
        results_by_task_id = {
            item["task_id"]: item
            for item in tool_results
        }

        current_result = results_by_task_id.get("current_dimension_period")
        previous_result = results_by_task_id.get("previous_dimension_period")

        if not current_result or not previous_result:
            raise ValueError("Missing current_dimension_period or previous_dimension_period result")

        if not current_result.get("success") or not previous_result.get("success"):
            raise ValueError("Current or previous dimension period query failed")

        current_rows = current_result.get("data", {}).get("rows", [])
        previous_rows = previous_result.get("data", {}).get("rows", [])

        current_map = {
            str(row.get("dimension_value")): row.get("value", 0) or 0
            for row in current_rows
        }

        previous_map = {
            str(row.get("dimension_value")): row.get("value", 0) or 0
            for row in previous_rows
        }

        dimension_values = sorted(
            set(current_map.keys()) | set(previous_map.keys())
        )

        rows = []

        for dimension_value in dimension_values:
            rows.append({
                "dimension_value": dimension_value,
                "current_value": current_map.get(dimension_value, 0),
                "previous_value": previous_map.get(dimension_value, 0),
            })

        return {
            "dimension": aggregation_plan.get("dimension"),
            "compare_mode": aggregation_plan.get("compare_mode"),
            "rows": rows,
        }

    if aggregation_type == "trend_by_dimension":
        series_map = {}

        for item in tool_results:
            query_plan = item.get("query_plan", {})
            params = query_plan.get("params", [])

            time_label = params[0] if params else None

            if not item.get("success"):
                continue

            rows = item.get("data", {}).get("rows", [])

            for row in rows:
                dimension_value = str(row.get("dimension_value"))
                value = row.get("value", 0) or 0

                if dimension_value not in series_map:
                    series_map[dimension_value] = []

                series_map[dimension_value].append({
                    "time_label": time_label,
                    "value": value,
                })

        if not series_map:
            raise ValueError("No valid trend_by_dimension data")

        return {
            "dimension": aggregation_plan.get("dimension"),
            "grain": aggregation_plan.get("grain", "day"),
            "series": series_map,
            "series_count": len(series_map),
        }

    return {
        "tool_results": tool_results,
    }


def plan_tasks_node(state: AgentState) -> AgentState:
    original_question = state["question"]

    if state.get("is_follow_up"):
        question_for_llm = state.get("resolved_question") or original_question
    else:
        question_for_llm = original_question

    request_id = state.get("request_id", "langgraph-session-test")
    start_ms = now_ms()

    prompt = f"""
你是 AI Data Agent 的语义解析器。

你只能输出 JSON，不要输出解释，不要使用 Markdown。

当前支持的业务指标：

metric: user_count
业务含义：用户数量
说明：
- 可用于统计某时间段新增用户数量
- 可用于趋势分析、分组分析、TopN分析、分布分析、对比分析

时间参数规则：
1. 如果用户问“某日新增用户”，则：
   start_time = 当天日期
   end_time = 次日日期

2. 如果用户问“某个日期范围的趋势”，则：
   start_time = 起始日期
   end_time = 结束日期的次日
   grain = day

3. 如果用户问“相比/对比/增长/下降”，只输出当前周期 start_time/end_time，系统会自动生成对比周期。

4. 如果用户问“按某个维度统计”或“各用户等级”，可以输出 dimension；如果不能确定，可以不输出，系统会从语义配置中解析。

用户问题：
{question_for_llm}

输出格式：

{{
  "metric": "user_count",
  "params": {{
    "start_time": "YYYY-MM-DD",
    "end_time": "YYYY-MM-DD",
    "grain": "day",
    "dimension": "可选",
    "limit": "可选"
  }}
}}
"""

    parsed = invoke_bedrock_json(prompt)

    parsed["user_question"] = original_question
    parsed["question"] = question_for_llm
    parsed["original_question"] = question_for_llm

    aggregation_plan = build_aggregation_plan(parsed)

    return {
        **state,
        "aggregation_plan": aggregation_plan,
        "tasks": aggregation_plan["tasks"],
        "request_id": request_id,
        "error": None,
        "trace": {
            "request_id": request_id,
            "question": original_question,
            "resolved_question": question_for_llm,
            "is_follow_up": state.get("is_follow_up"),
            "reset_context": state.get("reset_context"),
            "context_used": bool(
                state.get("is_follow_up")
                and state.get("inherited_context")
            ),
            "context_strategy": state.get("context_strategy"),
            "inherited_context": state.get("inherited_context"),
            "start_ms": start_ms,
            "steps": [
                {
                    "step": "plan_tasks",
                    "status": "success",
                    "output": {
                        "parsed": parsed,
                        "aggregation_plan": aggregation_plan,
                    },
                    "timestamp_ms": now_ms(),
                }
            ],
        },
    }


def compile_queries_node(state: AgentState) -> AgentState:
    query_plans = []
    compile_errors = []

    for task in state["tasks"]:
        try:
            metric_def = resolve_metric(task["metric"])
            query_plan = compile_metric_query(task, metric_def)
            query_plans.append(query_plan)

        except Exception as e:
            compile_errors.append({
                "task_id": task.get("task_id"),
                "task_name": task.get("task_name"),
                "metric": task.get("metric"),
                "error": str(e),
            })

    trace = state.get("trace", {})
    steps = trace.get("steps", [])

    steps.append({
        "step": "compile_queries",
        "status": "partial_success" if compile_errors else "success",
        "output": {
            "query_plans": query_plans,
            "compile_errors": compile_errors,
        },
        "timestamp_ms": now_ms(),
    })

    trace["steps"] = steps

    return {
        **state,
        "query_plans": query_plans,
        "compile_errors": compile_errors,
        "error": None,
        "trace": trace,
    }


def execute_queries_node(state: AgentState) -> AgentState:
    tool_results = []

    for query_plan in state.get("query_plans", []):
        start_ms = now_ms()

        try:
            result = invoke_sql_executor_with_query_plan(
                query_plan=query_plan,
                request_id=state["request_id"],
            )

            success = result.get("success", False)
            data = result.get("data")
            error = result.get("error")

        except Exception as e:
            success = False
            data = None
            error = str(e)

        end_ms = now_ms()
        latency_ms = end_ms - start_ms

        tool_results.append(
            build_tool_result(
                task_id=query_plan["task_id"],
                task_name=query_plan["task_name"],
                success=success,
                data=data,
                error=error,
                query_plan=query_plan,
                latency_ms=latency_ms,
            )
        )

    has_error = any(not r["success"] for r in tool_results)

    trace = state.get("trace", {})
    steps = trace.get("steps", [])

    steps.append({
        "step": "execute_queries",
        "status": "partial_success" if has_error else "success",
        "output": {
            "tool_results": tool_results,
        },
        "timestamp_ms": now_ms(),
    })

    trace["steps"] = steps

    return {
        **state,
        "tool_results": tool_results,
        "error": None,
        "trace": trace,
    }


def summarize_node(state: AgentState) -> AgentState:
    aggregation_type = state.get("aggregation_plan", {}).get("aggregation_type", "normal")

    template = load_summary_template(aggregation_type)

    prompt = template.format(
        question=state.get("question"),
        tasks=state.get("tasks"),
        query_plans=state.get("query_plans"),
        tool_results=state.get("tool_results"),
        aggregation_result=state.get("aggregation_result"),
        compile_errors=state.get("compile_errors"),
    )

    answer = invoke_bedrock_text(prompt)

    trace = state.get("trace", {})
    steps = trace.get("steps", [])

    steps.append({
        "step": "summarize",
        "status": "success",
        "output": {
            "aggregation_type": aggregation_type,
            "template": f"{aggregation_type}.txt",
            "answer": answer,
        },
        "timestamp_ms": now_ms(),
    })

    trace["steps"] = steps
    trace["answer"] = answer
    trace["end_ms"] = now_ms()
    trace["total_latency_ms"] = trace["end_ms"] - trace["start_ms"]

    trace_file = write_trace(state["request_id"], trace)

    return {
        **state,
        "answer": answer,
        "trace": trace,
        "trace_file": trace_file,
    }
    

def route_after_memory(state: AgentState) -> str:
    decision = can_answer_from_memory(state)

    print("route_after_memory:")
    print("  is_follow_up =", state.get("is_follow_up"))
    print("  inherited_context keys =", (state.get("inherited_context") or {}).keys())
    print("  has last_analysis =", bool((state.get("inherited_context") or {}).get("last_analysis")))
    print("  question =", state.get("question"))
    print("  decision =", decision)

    if decision:
        return "answer_from_memory"

    return "plan_tasks"
    

def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("load_memory", load_memory_node)
    workflow.add_node("answer_from_memory", answer_from_memory_node)
    workflow.add_node("plan_tasks", plan_tasks_node)
    workflow.add_node("compile_queries", compile_queries_node)
    workflow.add_node("execute_queries", execute_queries_node)
    workflow.add_node("aggregation_analysis", aggregation_analysis_node)
    workflow.add_node("build_structured_insight", structured_insight_node)
    workflow.add_node("generate_follow_up_suggestions", follow_up_suggestions_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("save_memory", save_memory_node)

    workflow.set_entry_point("load_memory")

    workflow.add_conditional_edges(
        "load_memory",
        route_after_memory,
        {
            "answer_from_memory": "answer_from_memory",
            "plan_tasks": "plan_tasks",
        },
    )

    workflow.add_edge("answer_from_memory", "save_memory")

    workflow.add_edge("plan_tasks", "compile_queries")
    workflow.add_edge("compile_queries", "execute_queries")
    workflow.add_edge("execute_queries", "aggregation_analysis")
    workflow.add_edge("aggregation_analysis", "build_structured_insight")
    workflow.add_edge("build_structured_insight", "generate_follow_up_suggestions")
    workflow.add_edge("generate_follow_up_suggestions", "summarize")
    workflow.add_edge("summarize", "save_memory")
    workflow.add_edge("save_memory", END)

    return workflow.compile()


def save_memory_node(state: AgentState) -> AgentState:
    session_id = state.get("session_id", "default-session")
    session_data = state.get("memory") or default_session_data(session_id)

    aggregation_plan = state.get("aggregation_plan", {})
    used_memory_only = state.get("used_memory_only", False)
    answer_context = build_answer_context(state)

    session_data.setdefault("turns", []).append({
        "question": state.get("question"),
        "resolved_question": state.get("resolved_question"),
        "answer": state.get("answer"),
        "aggregation_type": aggregation_plan.get("aggregation_type"),
        "trace_file": state.get("trace_file"),
        "used_memory_only": state.get("used_memory_only", False),
        "follow_up_suggestion_count": len(state.get("follow_up_suggestions", [])),
    })

    session_data["last_answer"] = answer_context

    if not used_memory_only:
        analysis_context = build_analysis_context(state)
        session_data["last_analysis_context"] = analysis_context
        session_data["last_context"] = analysis_context
        session_data["last_follow_up_suggestions"] = (
            state.get("follow_up_suggestions") or []
        )
    else:
        session_data["last_context"] = (
            session_data.get("last_analysis_context")
            or session_data.get("last_context")
            or {}
        )

    save_session(session_id, session_data)

    return {
        **state,
        "memory": session_data,
    }
