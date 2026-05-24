# 后续 Roadmap

## 战略方向

下一阶段应该验证 Guided Analytics Follow-up，而不是 Autonomous Root Cause
Analysis。

系统应该做到：

- 回答当前问题
- 清晰表达结论
- 给出数据证据
- 识别值得注意的变化、异常或结构
- 建议可能的下一步问题
- 等待用户决定是否继续

这是走向 Agentic Analysis 的关键一步，因为它验证 AI 是否能引导一个分析对
话，而不是只回答一次性问题。

## 短期 Roadmap

### 1. Capability Catalog

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

### 2. Structured Insight

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

### 3. Follow-up Suggestion Generator

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

### 4. Memory Context Refinement

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

### 5. Follow-up Regression

为 suggestion quality 增加 regression cases。

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

1. 定义 Capability Catalog。
2. 增加 Structured Insight object。
3. 基于 insight 和 capabilities 生成 Follow-up Suggestions。
4. 在 memory 中分离 suggestions 和 last real analysis。
5. 增加 Follow-up Suggestion Regression。

这条路线最符合当前项目目标：

```text
from answer bot
to guided analytics agent
to agentic analytics platform
```
