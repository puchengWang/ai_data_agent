from langgraph.graph import StateGraph, END
from app.observability.tracer import now_ms, write_trace
from app.protocols.query_protocol import build_tool_result
from app.planner.aggregation_planner import build_aggregation_plan
# from app.planner.comparison_engine import calculate_change
from app.analysis.operator_registry import OPERATOR_REGISTRY

from app.summary.summary_template_loader import load_summary_template
from app.analysis.operator_executor import execute_analysis_operators

from app.state import AgentState
from app.llm.bedrock_client import invoke_bedrock_json, invoke_bedrock_text
from app.semantic.semantic_engine import resolve_metric
from app.semantic.query_compiler import compile_metric_query
from app.tools.lambda_sql_tool import invoke_sql_executor_with_query_plan

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
    question = state["question"]
    start_ms = now_ms()

    prompt = f"""
你是 AI Data Agent 的语义解析器。
你只能输出 JSON，不要输出解释，不要使用 Markdown。
当前支持的业务指标：

metric: user_count

业务含义：用户数量
说明：
- 可用于统计某时间段新增用户数量
- 可用于统计截止某日用户总数
- 可用于普通用户数量查询
- 可用于趋势分析

请从用户问题中识别：

1. metric
2. params

时间参数规则：
1. 如果用户问“某日新增用户”，则：
   start_time = 当天日期
   end_time = 次日日期

2. 如果用户问“最近N天趋势”，则：
   start_time = 起始日期
   end_time = 结束日期的次日
   grain = day

3. 如果用户问“2026-05-10 到 2026-05-17 的趋势”，则：
   start_time = 2026-05-10
   end_time = 2026-05-18
   grain = day

4. 如果用户问“相比/对比/增长/下降”，保留当前周期 start_time/end_time，后续系统会自动生成对比周期。


用户问题：

{question}

输出格式：

{{

  "question": "{question}",
  "metric": "user_count",
  "params": {{
    "start_time": "YYYY-MM-DD",
    "end_time": "YYYY-MM-DD",
    "grain": "day"
  }}
}}

"""

    parsed = invoke_bedrock_json(prompt)

    # 生产建议：原始问题由系统维护，不信任 LLM 返回的 question
    parsed["original_question"] = question
    parsed["question"] = question

    aggregation_plan = build_aggregation_plan(parsed)

    return {
        **state,
        "aggregation_plan": aggregation_plan,
        "tasks": aggregation_plan["tasks"],
        "request_id": state.get("request_id", "langgraph-aggregation-test-001"),
        "error": None,
        "trace": {
            "request_id": state.get("request_id", "langgraph-aggregation-test-001"),
            "question": question,
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
    
def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("plan_tasks", plan_tasks_node)
    workflow.add_node("compile_queries", compile_queries_node)
    workflow.add_node("execute_queries", execute_queries_node)
    workflow.add_node("aggregation_analysis", aggregation_analysis_node)
    workflow.add_node("summarize", summarize_node)

    workflow.set_entry_point("plan_tasks")

    workflow.add_edge("plan_tasks", "compile_queries")
    workflow.add_edge("compile_queries", "execute_queries")
    workflow.add_edge("execute_queries", "aggregation_analysis")
    workflow.add_edge("aggregation_analysis", "summarize")
    workflow.add_edge("summarize", END)

    return workflow.compile()