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

然后等待我下一步指令。
```


### session结束时，输入prompt
```
请根据本次 session 的讨论、分析、设计和代码修改：
更新项目 context markdown 文件。

请分别输出：

1. current_status.md
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

请直接输出 markdown 内容。
```