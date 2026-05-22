from langgraph.graph import StateGraph, END
from app.observability.tracer import now_ms, write_trace
from app.protocols.query_protocol import build_tool_result

from app.state import AgentState
from app.llm.bedrock_client import invoke_bedrock_json, invoke_bedrock_text
from app.semantic.semantic_engine import resolve_metric
from app.semantic.query_compiler import compile_metric_query
from app.tools.lambda_sql_tool import invoke_sql_executor_with_query_plan


def plan_tasks_node(state: AgentState) -> AgentState:
    question = state["question"]
    start_ms = now_ms()

    prompt = f"""
你是 AI Data Agent 的任务规划器。

你只能输出 JSON，不要输出解释，不要使用 Markdown。

当前系统支持的业务指标：

metric: user_count
业务含义：用户数量
说明：
- 可以用于统计当前用户总数
- 可以用于统计截止某日期的用户总数
- 可以用于统计某一天或某个时间段内的用户数量变化

时间参数规则：
1. 如果问题是“某天新增多少用户”，输出 start_time 和 end_time
   例如：2026-05-14 新增用户
   start_time = 2026-05-14
   end_time = 2026-05-15

2. 如果问题是“截止某天用户总数”，输出 end_time
   例如：截止 2026-05-14 用户总数
   end_time = 2026-05-15

3. 如果一个问题包含多个统计需求，请拆成多个 tasks。

用户问题：
{question}

请输出如下 JSON：

{{
  "tasks": [
    {{
      "task_id": "task_001",
      "task_name": "任务名称",
      "metric": "user_count",
      "params": {{
        "start_time": "YYYY-MM-DD",
        "end_time": "YYYY-MM-DD"
      }}
    }}
  ]
}}
"""

    parsed = invoke_bedrock_json(prompt)

    return {
        **state,
        "tasks": parsed["tasks"],
        "request_id": state.get("request_id", "langgraph-multitask-test-001"),
        "error": None,
        "trace": {
            "request_id": state.get("request_id", "langgraph-multitask-test-001"),
            "question": question,
            "start_ms": start_ms,
            "steps": [
                {
                    "step": "plan_tasks",
                    "status": "success",
                    "output": parsed,
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
    prompt = f"""
你是一个企业数据分析助手。

请根据用户问题、任务列表、查询计划、执行结果和错误信息，生成简洁、可信的中文回答。

要求：
1. 不要输出 JSON
2. 不要解释底层代码
3. 不要编造额外信息
4. 每个子问题都要回答
5. 如果某个任务成功，正常回答结果
6. 如果某个任务失败，明确说明该子问题暂时无法回答，并给出失败原因
7. 如果部分成功部分失败，要先回答成功项，再说明失败项

用户问题：
{state["question"]}

任务列表：
{state.get("tasks")}

查询计划：
{state.get("query_plans")}

编译错误：
{state.get("compile_errors")}

执行结果：
{state.get("tool_results")}

请直接输出最终中文回答。
"""

    answer = invoke_bedrock_text(prompt)

    trace = state.get("trace", {})
    steps = trace.get("steps", [])

    steps.append({
        "step": "summarize",
        "status": "success",
        "output": {
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
    workflow.add_node("summarize", summarize_node)

    workflow.set_entry_point("plan_tasks")

    workflow.add_edge("plan_tasks", "compile_queries")
    workflow.add_edge("compile_queries", "execute_queries")
    workflow.add_edge("execute_queries", "summarize")
    workflow.add_edge("summarize", END)

    return workflow.compile()