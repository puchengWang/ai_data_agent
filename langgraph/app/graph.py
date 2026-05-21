from langgraph.graph import StateGraph, END

from app.state import AgentState
from app.llm.bedrock_client import invoke_bedrock_json, invoke_bedrock_text
from app.semantic.semantic_engine import resolve_metric
from app.semantic.query_compiler import compile_metric_query
from app.tools.lambda_sql_tool import invoke_sql_executor_with_query_plan


def understand_question_node(state: AgentState) -> AgentState:
    question = state["question"]

    prompt = f"""
你是 AI Data Agent 的语义解析器。

你只能输出 JSON，不要输出解释，不要使用 Markdown。

当前系统只支持一个业务指标：

metric: user_count
业务含义：用户数量
说明：统计 users 表中的用户数量
时间参数：
- start_time
- end_time

用户问题：
{question}

请输出如下 JSON：

{{
  "metric": "user_count",
  "params": {{
    "start_time": "YYYY-MM-DD",
    "end_time": "YYYY-MM-DD"
  }}
}}
"""

    parsed = invoke_bedrock_json(prompt)

    return {
        **state,
        "metric": parsed["metric"],
        "params": parsed["params"],
        "request_id": state.get("request_id", "langgraph-semantic-test-001"),
    }


def resolve_semantic_node(state: AgentState) -> AgentState:
    try:
        metric_def = resolve_metric(state["metric"])

        return {
            **state,
            "metric_def": metric_def,
            "error": None,
        }

    except Exception as e:
        return {
            **state,
            "error": str(e),
        }


def compile_query_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state

    try:
        query_plan = compile_metric_query(
            metric_name=state["metric"],
            metric_def=state["metric_def"],
            params=state["params"],
        )

        return {
            **state,
            "query_plan": query_plan,
            "error": None,
        }

    except Exception as e:
        return {
            **state,
            "error": str(e),
        }


def call_lambda_tool_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state

    result = invoke_sql_executor_with_query_plan(
        query_plan=state["query_plan"],
        request_id=state["request_id"],
    )

    if not result.get("success"):
        return {
            **state,
            "tool_result": result,
            "error": result.get("error", "Unknown Lambda tool error"),
        }

    return {
        **state,
        "tool_result": result,
        "error": None,
    }


def summarize_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return {
            **state,
            "answer": f"查询失败：{state['error']}",
        }

    prompt = f"""
你是一个企业数据分析助手。

请根据用户问题、业务指标定义、查询计划和查询结果，生成简洁、可信的中文回答。

要求：
1. 不要输出 JSON
2. 不要解释底层代码
3. 不要编造额外信息
4. 明确说明指标名称、时间范围和结果数值

用户问题：
{state["question"]}

业务指标：
{state["metric_def"]}

查询计划：
{state["query_plan"]}

查询结果：
{state["tool_result"]}

请直接输出最终中文回答。
"""

    answer = invoke_bedrock_text(prompt)

    return {
        **state,
        "answer": answer,
    }


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("understand_question", understand_question_node)
    workflow.add_node("resolve_semantic", resolve_semantic_node)
    workflow.add_node("compile_query", compile_query_node)
    workflow.add_node("call_lambda_tool", call_lambda_tool_node)
    workflow.add_node("summarize", summarize_node)

    workflow.set_entry_point("understand_question")

    workflow.add_edge("understand_question", "resolve_semantic")
    workflow.add_edge("resolve_semantic", "compile_query")
    workflow.add_edge("compile_query", "call_lambda_tool")
    workflow.add_edge("call_lambda_tool", "summarize")
    workflow.add_edge("summarize", END)

    return workflow.compile()