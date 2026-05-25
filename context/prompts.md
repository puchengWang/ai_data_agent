### 新建session后，输入prompt
```
请先阅读项目 ：

- context/AGENTS.md
- context/current_status.md
- context/architecture.md
- context/next_steps.md
理解当前项目状态后：

告诉我：

1. 你对项目的理解
2. 当前项目阶段
3. 当前优先事项
4. 下一步建议
5. 不要分析整个项目




然后等待我下一步指令。
```

### 模块级控制，降低token消耗
```
本次 Codex session 只处理【模块名】。

项目背景：
这是一个企业级 AI Data Analyst 项目。
当前目标是通过 LangGraph + Semantic Layer + Athena Executor 实现自然语言数据分析。

允许范围：
- 【模块目录】
- context/AGENTS.md
- context/architecture.md
- context/current_state.md
- context/next_steps.md

禁止范围：
- 不要修改其他模块
- 不要重构无关代码
- 不要扫描整个仓库
- 不要引入新的大规模架构变化

任务目标：
1. ...
2. ...
3. ...

输出要求：
1. 先说明计划
2. 再修改代码
3. 生成相关的测试案例和执行命令，不要自动执行，人工手动执行。
```


### session结束时，输入prompt
```
请根据本次 session 的讨论、分析、设计和代码修改：
更新项目 context markdown 文件。

请分别输出：

1. current_status.md(只保存当前有效状态)
2. next_steps.md
3. architecture.md（如果架构发生变化）
4. 新的 decision log（如果有重要技术决策）
5. session_summary_YYYY_MM_DD.md

要求：

- 内容简洁
- 使用 markdown
- 只保留当前有效信息
- 删除过时内容
- 不要保留聊天过程
- 不要输出无意义解释
- 强调：
  - 当前项目状态
  - 已完成内容
  - 当前问题
  - 下一阶段计划
  - 新的架构决策
  - 风险与待确认事项

session summary 需要包含：

- 本次完成内容
- 修改模块
- 新决策
- 当前风险
- 下一步行动

并自动移除：

- 已完成 todo
- 已废弃方案
- 已确认无效的架构讨论

请直接输出 markdown 内容。
```