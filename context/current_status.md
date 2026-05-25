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

项目已经完成以下 MVP：

- Runtime MVP
- Semantic System MVP
- Query Planner MVP
- Analysis Operators MVP
- Memory + Session Context MVP
- Capability Catalog MVP
- Structured Insight MVP
- Follow-up Suggestion Generator MVP
- Memory Context Refinement MVP

当前阶段已经从基础分析闭环推进到：

```text
Guided Analytics Follow-up MVP
```

含义是：系统能回答当前问题，生成结构化洞察，给出受能力边界约束的下一步
建议，并在多轮对话中保留上一轮真实分析上下文。系统仍不自动执行根因分析，
下一步动作由用户决定。

## Product Beta 转换判断

从功能验证角度看，Guided Analytics Follow-up 阶段已经可以收口。自治分析、
自动根因分析、forecast、correlation、主动监控等能力可以作为后续单独阶段，
不应继续挤占当前 Product Beta Readiness 的优先级。

如果目标是内部可信用户试用，项目下一阶段可以从功能探索转向：

```text
Product Beta Readiness
```

完成 Product Beta Readiness 后，项目可定位为：

```text
Product Beta for trusted internal users
```

当前还不应定位为面向广泛生产用户的 production-ready 系统，因为仍缺少运行
入口、安全控制、权限、协议固化、错误恢复和部署治理。

进入 Product Beta 前，功能层面的主要欠缺是：

- Suggestion Selection / Reference Resolution：
  用户说“就看这个”“第二个”“按用户等级拆一下”时，系统需要稳定映射到上一
  轮 `last_follow_up_suggestions`。
- Suggestions 展示策略：
  目前 suggestions 已进入 state、trace、memory，但最终回答暂不展示；需要
  决定由 API/UI 单独展示，还是由 summary prompt 展示。
- 更强的 Dimension Resolver：
  当前维度解析仍偏规则化，需要更稳定支持“用户等级”“等级”“level”“会员等
  级”等表达。
- 真实 Bedrock 端到端验证：
  当前真实 Bedrock Anthropic 调用受访问策略限制，Product Beta 前需要恢复或
  替换可用 LLM 路径。

进入 Product Beta 前，工程和安全层面的主要欠缺是：

- Runtime API：当前 `main.py` 仍是 demo 入口，需要稳定的 `/analyze` 或等价
  调用入口。
- SQL Safety Guardrail：需要 read-only、allowlist、semantic table/field 校
  验、timeout 和 row limit。
- Query / Tool Protocol：需要明确 scalar、rows、error、partial success 的
  标准结构。
- Error Response UX：Bedrock、Lambda、Aurora、SQL、无数据、语义无法识别时
  需要稳定用户响应，而不是暴露 stack trace。
- Secrets 和 runtime artifacts 管理：`.env`、trace、session、测试输出、DB
  credentials 需要明确保护和保留策略。
- Regression CI：当前已有脚本，但还需要聚合成 beta readiness 命令，并尽量
  进入 CI。
- Minimal Beta Documentation：需要说明支持范围、不支持范围、运行方式、排
  障方式和 known issues。

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

当前状态：MVP 已完成，仍不是生产级。

已实现：

- session JSON storage。
- 使用 Bedrock 判断 context strategy。
- follow-up 识别。
- 对“哪个等级下降最多？”这类问题支持 memory-only answer。
- follow-up regression tests。
- `last_analysis_context`、`last_answer`、`last_follow_up_suggestions` 分层。
- memory-only answer 不再覆盖上一轮真实分析上下文。
- Structured Insight 被写入 memory。
- Follow-up Suggestions 被写入 memory。
- 三轮 follow-up regression 可验证：
  - 第一轮真实分析写入 `last_analysis_context`
  - 第二轮 memory-only answer 不覆盖真实分析上下文
  - 第三轮仍能继承第一轮真实分析上下文

当前限制：

- Follow-up Suggestions 已是一等结构化输出，但暂不展示在 summary prompt 中。
- 用户选择 suggestion 后的自然语言承接仍依赖 context resolver，后续需要更强
  的 suggestion matching。
- 目前 Follow-up Generator 是规则驱动 MVP，不是生产级排序/推荐系统。
- 真实 Bedrock Anthropic 调用当前存在访问限制，端到端验证需要 mock Bedrock。

### Capability Catalog、Structured Insight 和 Suggestions

当前状态：MVP 已完成。

已实现：

- Capability Catalog 从 semantic config 和 operator mapping 派生当前真实能力。
- 当前能力边界：
  - metric：`user_count`
  - dimension：`level`
  - analysis types：`normal`、`compare`、`trend`、`group_by`、`top_n`、
    `distribution`、`compare_by_dimension`、`trend_by_dimension`
  - operators：`growth_rate`、`contribution`、`peak_valley`、`volatility`、
    `basic_anomaly`
- Structured Insight 生成：
  - `main_conclusion`
  - `evidence`
  - `interesting_points`
  - `limitations`
  - `available_drilldowns`
  - `suggestion_context`
- Follow-up Suggestion Generator 基于 insight 和 catalog 生成 1 到 4 条建议。
- 建议会经过 Capability Catalog 校验，不建议不存在的 `channel`、`region`、
  `device`、`revenue` 等能力。

当前限制：

- Suggestions 暂不进入最终自然语言回答。
- Suggestions 文案和排序仍是 MVP 规则。
- 尚未实现用户点击/选择 suggestion 后的专门路由。

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
- memory-only should preserve last analysis（三轮上下文保持验证）

这说明在当前单 metric、单 table 范围内，核心 MVP 闭环已经跑通。

2026-05-25 更新后的验证结果：

- `validate_capability_catalog.py`：`errors: 0`
- `validate_structured_insight.py`：`total: 8`，`failed: 0`
- `validate_follow_up_suggestions.py`：`total: 8`，`failed: 0`
- `validate_memory_context_refinement.py`：`errors: 0`
- `run_local_full_loop_with_mock_bedrock.py`：`success: true`
- `run_follow_up_regression.py --mock-bedrock`：`Failed: 0`
- `graph build`：`graph build ok`

Mock Bedrock 完整闭环验证：

```text
question: 2026-05-21新增用户量是多少
mode: mock_bedrock_real_graph_and_sql_tool
SQL result: 1595
```

该验证 mock 了 Bedrock JSON parsing、Bedrock summary 和 memory context strategy，
但保留真实 LangGraph workflow、Query Compiler、Lambda SQL Tool、Aurora 查询、
Analysis、Structured Insight、Follow-up Suggestions 和 Memory 写入。

当前真实 Bedrock 端到端验证阻塞：

```text
ValidationException:
Access to Anthropic models is not allowed from unsupported countries,
regions, or territories.
```

这属于 Bedrock Anthropic 模型访问策略或运行环境限制，不是当前闭环代码问题。

## 当前最大产品缺口

最大产品缺口已经从“是否能生成 guided follow-up”转为：

```text
用户如何稳定地选择、确认并执行系统给出的下一步建议？
```

也就是说，下一阶段重点不是证明 suggestions 能生成，而是让 suggestions 成为
更稳定的交互入口，并继续保持 capability-aware 和 evidence-backed。

## 当前最大架构缺口

当前系统已经证明了 fixed workflow 加 guided follow-up 的 MVP 能力，但还不是
flexible analysis dialog。

下一步应该引入：

- 更强的 suggestion matching / selection handling
- 更明确的 query/tool result protocol
- 更强的 dimension resolver
- 更完整的 follow-up regression 和 mock Bedrock regression
- 真实 Bedrock 可用环境下的端到端验证

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
- Capability-aware Follow-up Suggestions。
- Structured Insight 作为 analysis 和 guidance 之间的稳定接口。
- Memory Context Refinement，保证 memory-only turn 不覆盖真实分析上下文。

下一阶段应该聚焦：

```text
Product Beta Readiness
```

优先级应从“继续增加分析功能”转为“让当前 Guided Analytics 能力可运行、可
控、可解释、可恢复”。自治分析应作为 Product Beta 之后的新阶段。
