### Analysis Operators 第一批 Operators

建议先做这几个：

Operator

作用

适用场景

growth_rate

计算变化值和变化率

compare / compare_by_dimension

peak_valley

找最高点和最低点

trend / trend_by_dimension

contribution

计算占比贡献

distribution / group_by

volatility

计算波动程度

trend

basic_anomaly

简单异常识别

trend



### 总能力五大类
类别

Operators

作用

基础变化分析

growth_rate, delta, percent_change

判断增长、下降、变化幅度

趋势分析

peak_valley, moving_average, volatility, trend_direction

判断趋势、峰值、波动、是否持续上升/下降

维度分析

contribution, ranking, share, top_contributor, bottom_contributor

找出哪个维度贡献最大、下降最多、占比最高

异常分析

basic_anomaly, z_score_anomaly, threshold_alert, seasonality_check

判断是否异常、是否超过阈值

诊断分析

driver_analysis, root_cause_candidate, segment_compare, funnel_dropoff

开始回答“为什么变化”



### 实施顺序
第一批：基础 operators
growth_rate
peak_valley
contribution
volatility
basic_anomaly

第二批：BI operators
ranking
share
moving_average
trend_direction
top_contributor

第三批：诊断 operators
segment_compare
driver_analysis
root_cause_candidate
funnel_dropoff

第四批：预测 operators
forecast
seasonality
expected_range

第五批：自主分析 operators
auto_drilldown
next_best_question
insight_scoring