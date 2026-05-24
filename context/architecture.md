# 架构说明

## 高层架构

当前 AI Data Agent 的主链路是：

```text
User Question
-> LangGraph Runtime
-> Session Memory / Context Resolver
-> Bedrock Semantic Parser
-> Aggregation Planner
-> Semantic Engine
-> Query Compiler
-> Lambda SQL Executor
-> Aurora MySQL
-> Analysis Operators
-> Bedrock Summary
-> Trace / Session Storage
```

系统当前是为了在较小 semantic scope 内验证 Agentic Analytics 闭环。

## 项目结构

```text
.
├── README.md
├── 03Analysis Operators.md
├── context/
│   ├── AGENTS.md
│   ├── current_status.md
│   ├── architecture.md
│   └── next_steps.md
├── lambda/
│   └── db-connector.py
└── langgraph/
    ├── README.md
    ├── main.py
    ├── requirements.txt
    ├── app/
    │   ├── graph.py
    │   ├── config.py
    │   ├── state.py
    │   ├── llm/
    │   ├── tools/
    │   ├── semantic/
    │   ├── planner/
    │   ├── analysis/
    │   ├── memory/
    │   ├── summary/
    │   ├── protocols/
    │   └── observability/
    ├── semantic_configs/
    ├── semantic_generator/
    ├── ddl/
    ├── tests/
    ├── sessions/
    └── traces/
```

## 核心入口

### 本地 Demo 入口

`langgraph/main.py`

该文件构建 graph 并用硬编码 initial state 调用。它是本地验证入口，不是生产
API。

### Runtime Graph 入口

`langgraph/app/graph.py`

`build_graph()` 创建 LangGraph workflow，是当前系统真正的运行核心。

## LangGraph Workflow

当前 workflow：

```text
load_memory
  -> route_after_memory
      -> answer_from_memory -> save_memory -> END
      -> plan_tasks
          -> compile_queries
          -> execute_queries
          -> aggregation_analysis
          -> summarize
          -> save_memory
          -> END
```

### 节点说明

- `load_memory`：加载 session data，判断当前问题是否继承上一轮上下文。
- `answer_from_memory`：部分 follow-up question 可直接基于上一轮 structured
  analysis 回答，不重新查询。
- `plan_tasks`：调用 Bedrock 解析 metric 和 params，再生成 aggregation plan。
- `compile_queries`：解析 metric definition，将 tasks 编译为 query_plan SQL。
- `execute_queries`：把每个 query_plan 发给 Lambda。
- `aggregation_analysis`：把 tool results 转成 analysis input，并执行 operators。
- `summarize`：加载 summary template，调用 Bedrock 生成最终回答。
- `save_memory`：把 turn data 和 last context 写入 session JSON。

## 数据流

### 1. 用户问题

输入 state 通常包含：

```json
{
  "session_id": "optional-session-id",
  "question": "user question",
  "request_id": "optional-request-id"
}
```

### 2. Memory Resolution

`app/memory/context_resolver.py` 使用：

- reset keywords
- Bedrock context strategy classifier
- last session context

输出包括：

- `resolved_question`
- `is_follow_up`
- `reset_context`
- `context_strategy`
- `inherited_context`

### 3. Semantic Parsing

`plan_tasks_node` 向 Bedrock 请求 JSON：

```json
{
  "metric": "user_count",
  "params": {
    "start_time": "YYYY-MM-DD",
    "end_time": "YYYY-MM-DD",
    "grain": "day",
    "dimension": "optional",
    "limit": "optional"
  }
}
```

当前限制：prompt 明确围绕 `user_count`。

### 4. Aggregation Planning

`app/planner/aggregation_planner.py` 判断 aggregation type 并生成 tasks。

当前支持：

- `normal`
- `compare`
- `trend`
- `group_by`
- `top_n`
- `distribution`
- `compare_by_dimension`
- `trend_by_dimension`

Planner 当前主要依赖规则和关键词。

### 5. Semantic Resolution 和 SQL Compilation

`app/semantic/semantic_engine.py` 从 `semantic_configs` 解析 metric。

`app/semantic/query_compiler.py` 将 task 编译成：

```json
{
  "protocol_version": "1.0",
  "task_id": "...",
  "task_name": "...",
  "metric": "...",
  "business_name": "...",
  "engine": "...",
  "datasource": "...",
  "query_type": "sql",
  "sql": "...",
  "params": [],
  "meta": {}
}
```

时间参数使用 SQL params；table、measure、dimension identifier 来自 semantic
config 和 task 字段。

### 6. Tool Execution

`app/tools/lambda_sql_tool.py` 调用 AWS Lambda：

```json
{
  "query_plan": {},
  "request_id": "..."
}
```

Lambda 应返回结构化 tool result。当前 snapshots 中既有 scalar `value`，也有
grouped `rows`。

### 7. Analysis Operators

`app/analysis/operator_mapping.py` 将 aggregation type 映射到 operators：

- compare -> growth_rate
- trend -> peak_valley、volatility、basic_anomaly
- group_by/top_n/distribution -> contribution
- compare_by_dimension -> growth_rate
- trend_by_dimension -> peak_valley、volatility、basic_anomaly

`app/analysis/operator_executor.py` 统一执行 operators 并生成 structured
operator results。

### 8. Summary

`app/summary/templates/*.txt` 保存不同 aggregation type 的 summary prompts。

`summarize_node` 会把以下数据填入 template：

- user question
- tasks
- query plans
- tool results
- aggregation result
- compile errors

Bedrock 返回最终中文回答。

### 9. Observability 和 Memory

Trace 写入 `langgraph/traces/`。

Session 写入 `langgraph/sessions/`。

当前 memory 保存：

- turn list
- last_context
- question
- resolved question
- aggregation type
- metric
- params
- tasks
- query plans
- aggregation result
- answer

## 配置管理

### Runtime Config

`langgraph/app/config.py` 从 `.env` 或环境变量加载：

- `AWS_REGION`
- `SQL_EXECUTOR_LAMBDA_NAME`
- `BEDROCK_MODEL_ID`

### Semantic Config

`langgraph/semantic_configs/metrics.yaml`

当前主要 metric：

- `user_count`
- table：`users`
- aggregation：`count`
- field：`rid`
- time_field：`atime`
- dimension：`level`

`langgraph/semantic_configs/tables.yaml`

定义 `users` 表、fields、semantic types 和 primary key。

`langgraph/semantic_configs/glossary.yaml`

定义基础业务词汇。

## AI 调用方式

当前 AI 调用通过 boto3 直接调用 Bedrock Runtime：

- `invoke_bedrock_json(prompt)`：要求模型返回 JSON text，再用 `json.loads`
  解析。
- `invoke_bedrock_text(prompt)`：返回自然语言文本。

当前参数：

- `temperature = 0`
- `max_tokens = 500`
- Anthropic Messages API body
- `anthropic_version = bedrock-2023-05-31`

当前 AI 负责：

- 解析 metric 和 params
- 判断 context inheritance
- 回答 memory-only follow-up
- 生成最终 summary

当前 AI 还不负责：

- 生成 Structured Insight
- 生成 capability-aware Follow-up Suggestions
- 自主选择多步诊断计划

## 架构优势

- 端到端 analytical loop 已经跑通。
- Semantic Layer 对 AI 输出有约束。
- Aggregation Planner 和 Operators 具备 MVP 扩展基础。
- Multi-task Query Planning 已验证。
- Summary prompts 已按 analysis type 拆分。
- Session Memory 和 follow-up routing 有第一版。
- Regression tests 覆盖了主要 MVP cases。

## 架构弱点

- Planner 仍依赖关键词和规则。
- Prompt 仍围绕单一 metric。
- Query execution protocol 需要明确 scalar result 和 rows result。
- Memory 只有单一 `last_context`，memory-only turn 可能覆盖真实分析上下文。
- Follow-up Suggestions 还不是结构化一等输出。
- Capability awareness 仍是隐式的。
- 安全控制仍是 MVP 水平。

## 下一阶段目标架构

在做完整 autonomy 之前，应先补：

```text
Capability Catalog
-> Structured Insight
-> Follow-up Suggestion Generator
-> Refined Memory Context
-> Follow-up Regression
```

这能保持系统处在 Guided Analytics 方向：

```text
分析当前数据
-> 解释结论
-> 建议下一步问题
-> 等待用户决定
```
