## ai_data_agent
AI数据智能体，帮助公司实现业务分析、运营分析、根因分析、商业价值探索

系统核心公式: AI + Semantic Graph + Memory + Analytics Intelligence

Semantic Graph: 是持续建设与系统质量的重中之重。

## 整体思路
### 思路说明
```txt
1. 因为系统属于从0到1，所以整个验证过程中，注重验证思路的成立与框架的能力支撑
2. 通过单个指标开发，验证框架能够实现上限需求，才会转回来横向扩充业务范围
3. 将整个验证过程划分了八个阶段；每个阶段都作为MVP，只注重其核心能力，最终确立后，才会进行扩充。
```

### 基本架构
```txt
AI Data Agent
├── Agent Runtime：LangGraph / Bedrock / Tool Calling
├── Semantic System：metrics / dimensions / tables / glossary
├── Query Planner：normal / compare / trend / group_by / top_n
├── Query Executor：Lambda / Aurora / 后续 Athena
├── Analysis Operators：增长率 / 分布 / 波动 / 异常
├── Memory：多轮上下文
└── Output：自然语言 / 图表 / 报告
```

### 第一阶段 Runtime MVP

目标： 完成整体技术框架的验证
```txt
✅ LangGraph
✅ Bedrock
✅ Lambda
✅ Aurora
✅ Semantic Engine MVP
✅ Multi Task
✅ Trace
✅ Error Isolation
```

结论: 完全达到单指标的框架MVP的验证目的

### 第二阶段 Semantic System MVP
目标: 通过语义程序，直接将DDL文件转换为系统所需的标准业务语义。

```txt
✅ metrics.yaml
✅ tables.yaml
✅ glossary.yaml
✅ semantic_generator
✅ semantic_loader
```
结果: 通过一个表的验证，确认其能够实现。


### 第三阶段 Query Planner
目标: 从简单统计型上升为分析型AI，支持环比/同比/趋势等，然后进行比较、ranking、分布/维度计算，然后上升到能解释和发现变化与异常。

```txt
✅ Aggregation Planner
Analysis Operators
Query DAG

Note:
1. 完成Aggregation Planner后，进行了回归测试，同时将summarize prompt进行了独立拆分，使其达到生产系统要求。
```

### 第四阶段 Multi Data Source 联合
目标: 通过athena 实现ES，MySQL, Redshift, BigQuery等多数据源的支持。

```txt
Athena Executor
Redshift Executor
ES Executor
BigQuery Executor
S3 Executor
```

### 第五阶段 Analytics Agent
目标: 达到分析水平，像个专业分析师

```txt
Python Tool
Chart Tool
Statistical Engine
```

### 第六阶段 Memory + Session Context
目标: 通过上下文存储和理解，实现多轮分析，可对某数据的持续钻取和追问分析。
```txt
Session Memory
Context Inheritance
Drill Down Memory
Conversation Semantic Context
Memory Compression
Semantic Memory
```

### 第七阶段 Production Engineering
目标: 完全达到生产系统要求，实现在aws 生态部署

```txt
Docker 化
Fargate 部署
API Gateway
Auth / RBAC
CloudWatch / OpenSearch Logs
CI/CD
Semantic Config Deployment
```

### 第八阶段 Analytics Agent
目标: 达到自治AI Data Agent，支持自主发现异常、发现问题、主动洞察、主动给出建议

```txt
Anomaly Detection
Insight Generation
Root Cause Analysis
Autonomous Planner
Scheduled Analysis
Alerting
Recommendation Engine
Self Reflection
```
