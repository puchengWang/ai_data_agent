# 当前状态

## 项目目的

AI Data Agent 是用于验证 Agentic Analytics 的 MVP。长期愿景是构建企业级
AI Data Agent Platform，基于企业内部数据支持业务分析、运营分析、根因分
析探索和商业洞察发现。

当前目标是验证可行性：

- AI 是否能通过 Semantic Layer 理解业务问题。
- AI 是否能生成受控的 query plan。
- 系统是否能对查询结果执行 Analysis Operators。
- 系统是否能生成有数据证据的业务结论。
- 系统是否能在多轮对话中保留分析上下文。
- 系统是否能引导用户提出下一步分析问题。

当前阶段不要求所有逻辑都完美或强大，重点是验证 Agentic Analysis 的主要环
节、实现难度和可能性。

## 当前阶段判断

项目已经完成或接近完成以下 MVP：

- Runtime MVP
- Semantic System MVP
- Query Planner MVP
- Analysis Operators MVP
- Memory + Session Context MVP

下一阶段应该是：

```text
Guided Analytics Follow-up MVP
```

含义是：系统给出结论、证据和下一步建议，但不自动执行根因分析。

## 已实现能力

### Runtime Architecture

当前状态：MVP 基础较稳。

已实现：

- LangGraph state workflow。
- Bedrock JSON parsing 和 text generation。
- Lambda tool call 执行 SQL。
- Aurora MySQL 作为当前 data source。
- 每次请求写 trace。
- compile、tool、operator 阶段有基础 error isolation。

主要文件：

- `langgraph/app/graph.py`
- `langgraph/app/llm/bedrock_client.py`
- `langgraph/app/tools/lambda_sql_tool.py`
- `lambda/db-connector.py`

### Semantic System

当前状态：MVP 中高成熟度。

已实现：

- `metrics.yaml`
- `tables.yaml`
- `glossary.yaml`
- semantic loader
- metric resolver
- dimension resolver
- DDL-to-YAML generator

当前 semantic scope：

- metric：`user_count`
- table：`users`
- dimension：`level`
- time field：`atime`

### Query Planning

当前状态：当前最重要的资产之一。

已支持的 analysis types：

- normal
- compare
- trend
- group_by
- top_n
- distribution
- compare_by_dimension
- trend_by_dimension

Planner 已经可以把一个用户问题拆成多个 query tasks，例如 compare 和 trend。

当前限制：

- aggregation type detection 仍主要依赖关键词和规则。
- Bedrock parsing prompt 仍以 `user_count` 为中心。
- 当前系统更像 guided workflow，而不是通用 autonomous planner。

### Analysis Operators

当前状态：MVP 核心资产。

已实现：

- `growth_rate`
- `peak_valley`
- `contribution`
- `volatility`
- `basic_anomaly`

Operator Runtime 能按 aggregation type 映射并执行对应 operators。

这是 Analytics Intelligence 层的雏形。

### Summary System

当前状态：可用，但需要升级为 Insight System。

已实现：

- 按 aggregation type 拆分的 summary prompt templates。
- 通过 Bedrock 生成最终自然语言回答。

当前限制：

- 当前输出以 prose 为主。
- Follow-up 需要 Structured Insight，不能只从最终中文回答里反推。

### Memory 和 Follow-up

当前状态：已验证，但仍脆弱。

已实现：

- session JSON storage。
- 使用 Bedrock 判断 context strategy。
- follow-up 识别。
- 对“哪个等级下降最多？”这类问题支持 memory-only answer。
- follow-up regression tests。

当前限制：

- memory-only answer 可能覆盖上一轮真实分析上下文。
- memory 应区分 last real analysis、last answer、last follow-up suggestions。
- Follow-up Suggestions 还不是一等输出。

## 验证证据

Regression coverage 已包含：

- normal user count
- compare user count
- trend user count
- group by level
- top N level
- distribution by level
- compare by dimension
- trend by dimension

Follow-up regression coverage 已包含：

- follow-up decline by level
- follow-up growth by level
- reset context and start new question
- complete new question should not inherit context

这说明在当前单 metric、单 table 范围内，核心 MVP 闭环已经跑通。

## 当前最大产品缺口

最大产品缺口不是自动根因分析，而是 guided follow-up：

```text
回答当前问题后，系统能否提出有证据、可执行、不过界的下一步问题？
```

这是下一阶段验证 Agentic Analysis 的关键能力。

## 当前最大架构缺口

当前系统证明了 fixed workflow，而不是 flexible analysis dialog。

下一步应该引入：

- Capability Catalog
- Structured Insight
- Follow-up Suggestion Generator
- 更清晰的 Memory Context 分层

这些任务应先于完整 Query DAG Runtime 或 Autonomous Analytics。

## 当前最大安全缺口

MVP 中仍存在一些需要控制的风险：

- Lambda 示例代码中存在数据库连接信息。
- 本地 `.env` 和 runtime artifacts 没有明确 `.gitignore` 保护。
- session 和 trace 可能包含 SQL、查询结果和业务上下文。
- Lambda 执行 query_plan SQL，后续扩展前需要 read-only / allowlist 控制。

这些不是当前最核心的产品验证任务，但需要避免 MVP 环境变成风险源。

## 总体评估

当前项目已经验证：

- AI + Semantic Layer + Query Planner + SQL Tool 的端到端闭环。
- 基础 Analysis Operators。
- Multi-task analytical planning。
- Natural-language summary generation。
- Session Memory 和 Follow-up handling 的第一版。

下一阶段应该聚焦：

```text
Insight + Follow-up Question Generation
```

这条路线最自然地把系统从 data answer bot 推向 guided analytics agent。
