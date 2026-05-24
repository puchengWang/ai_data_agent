# AI Data Agent 项目上下文

本仓库是一个用于验证 Agentic Analytics / AI Data Agent Platform 可行性的
MVP。当前目标不是优先建设生产级系统，而是探索 AI 是否能够基于企业内部数
据完成业务分析、运营分析、数据结论生成，并引导用户进行后续下钻。

## 项目目标

长期目标是构建企业级 AI Data Agent Platform，支持：

- 业务分析
- 运营分析
- Guided Drill-down Analysis
- 根因分析探索
- 商业洞察发现

当前阶段聚焦 AI Analytics 和 Guided Analytics，而不是完全自治的根因分析。
系统应该完成当前问题的数据分析，给出有证据的结论，并提出可继续追问的方
向。下一步是否执行，由用户决定。

## 当前阶段

项目已经验证了第一条核心闭环：

```text
自然语言问题
-> Bedrock 解析 metric 和 params
-> Semantic Layer 解析 metric/table/dimension
-> Aggregation Planner 生成一个或多个 task
-> Query Compiler 生成 query_plan SQL
-> Lambda 执行 query_plan
-> Aurora MySQL 返回数据
-> Analysis Operators 计算分析信号
-> Bedrock 生成总结
-> Session Memory 保存分析上下文
```

下一阶段的主要任务是 Follow-up MVP：

```text
当前分析结果
-> Structured Insight
-> 基于能力边界生成 Follow-up Suggestions
-> 用户选择下一步问题
```

注意：下一阶段不是 Autonomous Root Cause Analysis，而是 Guided Analytics。

## 核心原则

- 优先验证 Agentic Analysis 的可行性，不追求生产系统完整度。
- 优先做小而完整的端到端 MVP，不盲目横向扩展功能。
- AI 的输出必须受 Semantic Config 和 Capability Catalog 约束。
- Follow-up Suggestions 必须是当前系统可以执行的问题。
- Follow-up Suggestions 不能虚构不存在的 metric、dimension 或 data source。
- 用户决定下一步动作；系统只给出建议，不自动下钻。
- 必须保留真实分析上下文，不能让 memory-only 回答覆盖上一轮真实分析。

## 重要目录

- `README.md`：项目愿景和阶段规划。
- `langgraph/main.py`：本地 demo 入口。
- `langgraph/app/graph.py`：核心 LangGraph workflow。
- `langgraph/app/planner/aggregation_planner.py`：aggregation type 判断和 task 生成。
- `langgraph/app/semantic/`：semantic loading、metric resolving、query compiling。
- `langgraph/semantic_configs/`：当前语义配置。
- `langgraph/app/analysis/`：Analysis Operators 和 Operator Runtime。
- `langgraph/app/memory/`：Session Memory 和 context resolution。
- `langgraph/app/summary/templates/`：summary prompt templates。
- `langgraph/tests/`：regression 和 follow-up regression cases。
- `lambda/db-connector.py`：Lambda SQL executor 示例。

## 当前核心资产

- LangGraph runtime workflow。
- Bedrock JSON parsing 和 natural-language summarization。
- `metrics.yaml`、`tables.yaml`、`glossary.yaml` 组成的 Semantic Config。
- 支持 normal、compare、trend、group_by、top_n、distribution、
  compare_by_dimension、trend_by_dimension 的 Aggregation Planner。
- compare 和 trend 场景下的 Multi-task Planning。
- Analysis Operators：growth_rate、contribution、peak_valley、volatility、
  basic_anomaly。
- Session Memory 和 follow-up context resolution。
- Regression tests 和 trace outputs。

## 当前能力边界

当前 semantic scope 故意保持很小：

- 主要 metric：`user_count`
- 主要 table：`users`
- 主要 dimension：`level`
- 当前 executor：Lambda -> Aurora MySQL

除非已经加入 Semantic Config，不要假设系统存在 channel、region、device、
product、revenue、funnel 等指标或维度。

## 近期优先级

1. Capability Catalog
2. Structured Insight
3. Follow-up Suggestion Generator
4. Memory Context Refinement
5. Follow-up Regression

这些任务当前比 Multi Data Source、生产部署、Chart、Python Tool 或自主根因
分析更重要。

## 安全注意事项

虽然当前是 MVP，但仍需要保护验证环境：

- 不暴露 secrets。
- 不扩大 SQL 执行能力，保持 bounded read-only query。
- 不生成当前系统无法执行的 follow-up 建议。
- 不把 trace、session、`.env`、`__pycache__` 等运行产物当作项目上下文提交。
- 对 `sessions/`、`traces/`、`.env` 和本地 runtime artifacts 保持谨慎。

## 后续 Agent 工作方式

未来修改项目时：

- 先阅读当前代码和 Semantic Config。
- 保持改动小而聚焦，服务于 MVP 验证目标。
- 行为变化时补充或更新 regression cases。
- 优先增加结构化中间结果，而不是只依赖最终自然语言回答。
- Follow-up 行为必须 capability-aware 且 evidence-backed。
- 在分析闭环验证清楚前，不要过度投入生产基础设施。
