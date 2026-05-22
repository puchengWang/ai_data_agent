# AI Data Agent LangGraph & semantic layer  MVP

本项目用于验证：

```text
用户自然语言
↓
Bedrock 输出 metric + params
↓
Semantic Engine 解析 metric
↓
Query Compiler 生成 query_plan
↓
Lambda 执行 query_plan.sql
↓
Aurora 返回 value
↓
Bedrock 总结答案
```

通过自定义语义引擎， 实现整个技术闭环的验证。

## 安装依赖

```bash
python3.13 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

## 配置环境变量

复制：

```bash
cp .env.example .env
```

修改 `.env`：

```bash
AWS_REGION=ap-southeast-1
SQL_EXECUTOR_LAMBDA_NAME=你的Lambda函数名
```

本地需要有 AWS 凭证，可以通过以下任一方式提供：

```bash
aws configure
```

或使用已有的 AWS Profile：

```bash
export AWS_PROFILE=your-profile
```

## 第一步：运行 LangGraph

```bash
cd langgraph

python3.13 main.py
```

## 第二步: DDL转换为metrics 信息
```bash
python3.13 -m semantic_generator.generate --ddl ddl/users.sql
```


