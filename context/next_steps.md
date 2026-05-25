# 后续 Roadmap

## 战略方向

Guided Analytics Follow-up 的 MVP 已经完成。下一阶段应该转向 Product Beta
Readiness，而不是继续扩展 Autonomous Root Cause Analysis。

系统应该做到：

- 回答当前问题
- 清晰表达结论
- 给出数据证据
- 识别值得注意的变化、异常或结构
- 建议可能的下一步问题
- 等待用户决定是否继续

这是走向 Agentic Analysis 的关键一步，因为它验证 AI 是否能引导一个分析对
话，而不是只回答一次性问题。

当前功能阶段可收口为：

```text
Guided Analytics MVP+
```

下一阶段目标是：

```text
Product Beta for trusted internal users
```

Autonomous Analytics、自动根因分析、预测、相关性和主动监控应作为 Product
Beta 之后的独立阶段推进。

## 短期 Roadmap

### 1. Capability Catalog

当前状态：MVP 已完成。

建立一份结构化的系统能力清单，让系统知道自己当前能建议什么、不能建议什
么。

初始 catalog 可以很小：

```yaml
metrics:
  - user_count
dimensions:
  user_count:
    - level
analysis_types:
  - normal
  - compare
  - trend
  - group_by
  - top_n
  - distribution
  - compare_by_dimension
  - trend_by_dimension
operators:
  - growth_rate
  - contribution
  - peak_valley
  - volatility
  - basic_anomaly
```

目的：

- 防止 Follow-up Suggestions 虚构不存在的数据。
- 确保建议可以被当前系统执行。
- 为未来 Semantic Graph 和 Query DAG 打基础。

验收标准：

- Follow-up Generator 能读取可用 metrics 和 dimensions。
- 除非已加入 Semantic Config，否则不建议 channel、region、device 等维度。
- 每条建议都能映射到当前支持的 analysis type。

当前验证：

- `validate_capability_catalog.py` 已通过，`errors: 0`。
- 当前只暴露 `user_count` 和 `level`。

### 2. Structured Insight

当前状态：MVP 已完成。

在最终自然语言回答之前或同时，生成结构化分析摘要。

建议字段：

```json
{
  "main_conclusion": "...",
  "evidence": [],
  "interesting_points": [],
  "limitations": [],
  "available_drilldowns": [],
  "suggestion_context": {}
}
```

目的：

- 让 Follow-up Suggestions 有证据来源。
- 避免从最终自然语言回答中反向猜测。
- 在 analysis 和 guidance 之间建立稳定接口。

验收标准：

- compare result 能暴露 current value、previous value、change、change rate。
- trend result 能暴露 peak、valley、volatility、anomaly。
- group_by/distribution result 能暴露 top contributor 和 contribution rates。
- Structured Insight 被写入 memory。

当前验证：

- `validate_structured_insight.py` 已覆盖 8 个 snapshot cases，`failed: 0`。
- Structured Insight 已进入 state、trace 和 memory。

### 3. Follow-up Suggestion Generator

当前状态：MVP 已完成。

每次回答后生成 2 到 4 个建议追问，但不执行这些建议。

建议结构：

```json
{
  "question": "按用户等级看增长主要来自哪个等级？",
  "reason": "当前问题存在明显增长，可通过可用维度 level 拆解贡献。",
  "expected_analysis_type": "compare_by_dimension",
  "required_capability": {
    "metric": "user_count",
    "dimension": "level"
  }
}
```

初始 suggestion patterns：

- normal -> trend 或 group_by
- compare -> compare_by_dimension 或 trend
- trend -> 查看 peak/valley/anomaly date，或按可用 dimension 拆解
- group_by -> 查看 top dimension 的 trend，或和前一周期比较
- distribution -> 比较前一周期 distribution 是否变化
- top_n -> 查看 top item 的 trend 或和前一周期比较

验收标准：

- 建议问题是自然中文。
- 建议当前系统可执行。
- 建议受 Capability Catalog 约束。
- 建议只是选项，不自动执行。

当前验证：

- `validate_follow_up_suggestions.py` 已覆盖 8 个 snapshot cases，`failed: 0`。
- `run_local_full_loop_with_mock_bedrock.py` 已验证 mock Bedrock + 真实
  Lambda/Aurora 链路，`success: true`。
- Suggestions 已进入 state、trace 和 memory，但暂不展示在 summary prompt 中。

### 4. Memory Context Refinement

当前状态：MVP 已完成。

优化 Session Memory，保证多轮 Follow-up 能保留上一轮真实分析。

建议 memory 分层：

```json
{
  "last_analysis_context": {},
  "last_answer": {},
  "last_follow_up_suggestions": [],
  "turns": []
}
```

目的：

- 避免 memory-only answer 覆盖 last real analysis。
- 用户追问系统建议的问题时，能继承正确上下文。
- 让多轮 Guided Analytics 更稳定。

验收标准：

- memory-only turn 不会清空 `last_analysis_context`。
- Follow-up Suggestions 会被保存。
- Context Resolver 能在用户追问建议问题时使用上一轮真实分析。

当前验证：

- `validate_memory_context_refinement.py` 已通过，`errors: 0`。
- `run_follow_up_regression.py --mock-bedrock` 已通过，`Failed: 0`。
- 三轮 follow-up case 已验证 memory-only turn 不覆盖第一轮真实分析上下文。

### 5. Follow-up Regression

当前状态：MVP 已完成，后续继续扩展。

为 suggestion quality 和 memory context 增加 regression cases。

初始 cases：

- compare question 建议按 `level` 做 `compare_by_dimension`。
- trend question 建议检查 peak/anomaly 日期和可用 dimension。
- group_by question 建议查看 top dimension 的 trend 或 compare。
- distribution question 建议比较前一周期 distribution。
- normal question 建议查看 trend 和可用 dimension breakdown。

验证项：

- suggestion count 在合理范围内。
- 每条 suggestion 有 question 和 reason。
- 每条 suggestion 都能被 Capability Catalog 验证为可执行。
- 不建议不存在的 metric 或 dimension。
- 不自动执行 suggestion。
- memory-only answer 不覆盖 `last_analysis_context`。
- 第三轮 follow-up 仍能继承第一轮真实分析上下文。

当前 Bedrock 说明：

- 真实 Bedrock Anthropic 调用当前存在访问限制。
- 回归验证应优先使用 `--mock-bedrock` 模式，恢复权限后再补真实端到端验证。

## 下一步推荐

当前短期 Roadmap 前四项已经完成 MVP。下一步建议聚焦以下任务：

1. Suggestion Selection Handling

   让用户可以围绕系统建议继续追问，例如“就看这个”“第二个”“按用户等级拆
   一下”。系统需要把这些表达稳定映射到上一轮
   `last_follow_up_suggestions`。

2. Mock Bedrock Regression 标准化

   当前 Bedrock Anthropic 模型受访问策略限制。建议将 mock Bedrock 模式作为
   本地 regression 的正式路径，真实 Bedrock 作为环境可用时的补充验证。

3. Query / Tool Protocol Refinement

   明确 scalar、grouped、error、partial success 的返回结构，减少 analysis
   layer 对 tool result 形态的隐式假设。

4. Summary / Suggestion 展示策略

   当前 suggestions 已进入 state、trace、memory，但没有展示在最终回答中。
   后续需要决定是由 summary prompt 展示，还是由 API/UI 单独展示结构化建议。

5. Dimension Resolver 增强

   继续提升“用户等级 / 等级 / level / 会员等级”等表达的解析稳定性。

## Product Beta Readiness

Product Beta 的目标不是继续增加更多分析能力，而是让当前 Guided Analytics
能力具备可试用的产品形态。

目标定位：

```text
Product Beta for trusted internal users
```

不建议当前直接定位为广泛生产可用系统。Product Beta 之前至少应完成以下事
项。

### 1. Bedrock Access Recovery

当前真实 Bedrock Anthropic 调用存在访问策略限制：

```text
ValidationException:
Access to Anthropic models is not allowed from unsupported countries,
regions, or territories.
```

Product Beta 前需要恢复真实 LLM 路径：

- 确认 AWS region。
- 确认 Bedrock model access。
- 确认运行环境、VPN、代理或出口 IP。
- 必要时切换到可用 Bedrock 模型。
- 必要时增加 OpenAI-compatible fallback。

验收标准：

- 不使用 mock Bedrock 时，真实 `plan_tasks`、summary、context strategy 能
  跑通。
- 至少一条真实端到端 case 能完成 Bedrock -> Lambda -> Aurora -> Insight ->
  Suggestions。

### 2. Runtime API

当前 `main.py` 是 demo 入口，不是 product runtime。

建议提供最小 API：

```text
POST /analyze
```

请求：

```json
{
  "session_id": "...",
  "question": "..."
}
```

响应：

```json
{
  "answer": "...",
  "structured_insight": {},
  "follow_up_suggestions": [],
  "trace_id": "..."
}
```

验收标准：

- API 能复用现有 LangGraph workflow。
- 返回 answer、structured insight、suggestions 和 trace id。
- 不把内部 stack trace 直接返回给用户。

### 3. Suggestion Selection / Reference Resolution

当前 suggestions 已生成并保存，但用户选择 suggestion 的链路还不够稳定。

需要支持：

- “就看这个”
- “第二个”
- “按用户等级拆一下”
- “看刚才建议的趋势”

系统应能将这些表达映射到上一轮 `last_follow_up_suggestions`。

验收标准：

- 能识别用户选择的是第几条 suggestion。
- 能把 suggestion 转成可执行问题。
- 能继承上一轮 `last_analysis_context`。
- 选择 suggestion 不会越过 Capability Catalog。

### 4. SQL Safety Guardrail

当前 Lambda 执行 query_plan SQL，Product Beta 前需要最小安全约束。

建议：

- 只允许 `SELECT`。
- 禁止 `INSERT`、`UPDATE`、`DELETE`、`DROP`、`ALTER`。
- 只允许 Semantic Config 中声明的 table。
- 只允许 allowlisted metric、dimension、field。
- 强制 timeout。
- 对 grouped 查询强制 row limit。

验收标准：

- 非 SELECT SQL 被拒绝。
- 未声明 table/field 被拒绝。
- 错误以结构化 error result 返回。

### 5. Query / Tool Protocol Refinement

当前 tool result 已可用，但协议仍偏隐式。

建议明确：

```json
{
  "success": true,
  "data_type": "scalar",
  "data": {
    "value": 1595
  },
  "error": null,
  "meta": {}
}
```

失败结构：

```json
{
  "success": false,
  "error_code": "...",
  "error_message": "...",
  "retryable": false,
  "meta": {}
}
```

验收标准：

- scalar、rows、error、partial success 都有稳定结构。
- Analysis Operators 不再依赖过多隐式字段。

### 6. Error Response UX

Product Beta 一定会遇到失败场景，需要稳定用户响应。

需要覆盖：

- Bedrock failure
- Lambda timeout
- SQL error
- Aurora unavailable
- No data
- Semantic parsing failed
- Follow-up context missing

验收标准：

- 用户看到可理解的失败说明。
- trace 中保留技术细节。
- API 不直接暴露 Python stack trace。

### 7. Secrets 和 Runtime Artifacts 管理

需要明确保护：

- `.env`
- DB credentials
- Lambda secrets
- `sessions/`
- `traces/`
- `tests/outputs/`

验收标准：

- secrets 不进入 git。
- runtime artifacts 不作为项目上下文提交。
- trace/session 的保留策略明确。

### 8. Regression Test 聚合

当前已有多个验证脚本，Product Beta 前建议聚合成一个命令。

应包含：

```bash
validate_semantic_config.py
validate_capability_catalog.py
validate_structured_insight.py
validate_follow_up_suggestions.py
validate_memory_context_refinement.py
run_follow_up_regression.py --mock-bedrock
run_local_full_loop_with_mock_bedrock.py
```

建议新增：

```text
tests/run_beta_readiness.py
```

验收标准：

- 一条命令可跑完 beta readiness 本地检查。
- Bedrock 真实可用时可追加真实端到端检查。

### 9. Minimal Beta Documentation

Product Beta 前需要最小文档：

- 当前支持什么问题。
- 当前不支持什么问题。
- 当前 semantic scope。
- 如何运行 API。
- 如何运行 regression。
- 如何排查 Bedrock / Lambda / DB 问题。
- known issues。

验收标准：

- 内部试用者能理解系统能力边界。
- 开发者能复现本地验证和定位常见问题。

## Product Beta 前功能欠缺

如果只看功能，进入 Product Beta 前还缺：

1. Suggestion selection / reference resolution。
2. Suggestions 展示策略。
3. 更强的 dimension resolver。
4. 真实 Bedrock 端到端恢复。
5. 最小 API 入口。

这些完成后，功能侧可以支持可信内部用户试用。

## Product Beta 前非功能欠缺

如果看生产可试用性，还缺：

1. SQL safety guardrail。
2. Secrets / artifacts 管理。
3. Tool protocol 固化。
4. Error response UX。
5. Regression 聚合。
6. Minimal beta docs。

这些完成后，项目才更接近 Product Beta，而不是仅仅是一个功能 demo。

## 中期 Roadmap

### 1. 增强 Dimension Resolver

从简单 contains matching 升级到更强的语义匹配。

示例表达：

- 用户等级
- 等级
- level
- 会员等级
- 服务等级

期望输出应包含 confidence 和 candidate dimensions。

### 2. 将 Summary 升级为 Insight System

当前 summary 是 template-based prose generation。中期应升级为：

```text
aggregation_result
-> structured insight
-> final answer
-> follow-up suggestions
```

这样系统更稳定，也更容易测试。

### 3. 规范 Query 和 Tool Protocol

明确结果结构：

- scalar result：`{"value": number}`
- grouped result：`{"rows": []}`
- error result
- partial success result

这很重要，因为当前 analysis code 会根据 aggregation type 期待 `value` 或
`rows`。

### 4. 增加一个新 Metric 或一个新 Dimension

不要大规模扩展。只选一个很小的扩展，用来证明 Semantic System 可以横向复
用。

推荐顺序：

- 如果安全且数据可用，先给 `users` 增加一个 dimension。
- Follow-up 稳定后，再增加一个新 metric。

### 5. Query DAG Representation

引入轻量级 analysis steps 表示：

```text
parse -> plan -> query -> operator -> insight -> follow_up
```

此时不需要做完整 autonomous runtime。先让分析流程更容易检查、组合和测试。

## 长期 Roadmap

### 1. Semantic Graph

从独立 YAML 配置升级到业务语义图谱，表达：

- metrics
- dimensions
- entities
- events
- business processes
- relationships
- allowed drill-down paths

这是企业级 AI Analytics 的长期核心资产。

### 2. Query DAG Runtime

建设可以表达多步分析流程的 Analytics Workflow DAG。

未来可能的 flow：

```text
overall change
-> dimension breakdown
-> trend confirmation
-> distribution shift
-> evidence-backed conclusion
-> suggested next step
```

初期仍然可以保持 user-guided，不必直接变成全自动。

### 3. Advanced Analytics Operators

按层推进 operators。

第一批：

- ranking
- share
- moving_average
- trend_direction
- top_contributor

第二批：

- segment_compare
- driver_analysis
- root_cause_candidate
- funnel_dropoff

后续：

- forecast
- seasonality
- expected_range
- correlation

### 4. Autonomous Analytics

只有当 Guided Follow-up 和 Query DAG 稳定后，再探索 Autonomous Analytics：

- scheduled analysis
- proactive anomaly detection
- autonomous drill-down
- root-cause candidates
- recommendation engine
- self-reflection

这是长期 AI Analyst 方向，不是当前阶段重点。

### 5. Production Engineering

生产化阶段需要：

- secrets management
- read-only SQL enforcement
- auth / RBAC
- API Gateway
- ECS/Fargate 或等价部署
- CloudWatch / OpenSearch logs
- CI/CD
- Semantic Config deployment process

这些很重要，但不应挤占 Guided Analytics 验证工作。

## 当前不优先做什么

以下方向有价值，但不是当前瓶颈：

- Multi Data Source federation
- Athena / ES / BigQuery integration
- Python pandas/sklearn tool
- Chart / Visualization layer
- 复杂 forecast / correlation
- ECS / Fargate deployment
- API Gateway / Auth
- Cloud Monitoring
- Fully Autonomous Root Cause Analysis

它们应等系统证明自己能稳定生成可靠 Follow-up Suggestions 后再推进。

## 推荐的立即任务顺序

已完成：

1. 定义 Capability Catalog。
2. 增加 Structured Insight object。
3. 基于 insight 和 capabilities 生成 Follow-up Suggestions。
4. 在 memory 中分离 suggestions 和 last real analysis。
5. 增加 Follow-up Suggestion / Memory Context Regression。

新的立即任务：

1. Bedrock Access Recovery。
2. Runtime API。
3. Suggestion selection / reference resolution。
4. SQL Safety Guardrail。
5. Query / Tool Protocol Refinement。
6. Error Response UX。
7. Regression Test 聚合。
8. Minimal Beta Documentation。

这条路线最符合当前项目目标：

```text
from answer bot
to guided analytics agent
to product beta
to agentic analytics platform
```
