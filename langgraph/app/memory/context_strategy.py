from typing import Any, Dict

from app.llm.bedrock_client import invoke_bedrock_json


def detect_context_strategy(
    question: str,
    last_context: Dict[str, Any],
) -> Dict[str, Any]:

    if not last_context:
        return {
            "use_context": False,
            "reset_context": False,
            "reason": "no_previous_context",
        }

    prompt = f"""
你是 AI Data Agent 的上下文策略判断器。

你的任务是判断当前用户问题是否应该继承上一轮分析上下文。

上一轮问题：
{last_context.get("question")}

上一轮分析类型：
{last_context.get("aggregation_type")}

上一轮指标：
{last_context.get("metric")}

上一轮维度：
{last_context.get("dimension")}

上一轮参数：
{last_context.get("params")}

当前用户问题：
{question}

判断规则：

1. 如果当前问题明显是在继续分析上一轮，例如：
- 哪个下降最多
- 哪个增长最多
- 为什么
- 继续分析
- 那这个等级呢
- 和昨天比呢
- 按渠道看看
- 换个维度看

则：
use_context = true
reset_context = false

2. 如果当前问题明显是新主题或用户要求不要参考上文，例如：
- 重新开始
- 忽略上文
- 不要参考之前
- 新问题
- 单独分析这个
- 换个问题
- 看另一个指标

则：
use_context = false
reset_context = true

3. 如果当前问题本身已经包含完整时间范围、指标和维度，通常视为新问题：
use_context = false
reset_context = false

4. 如果无法确定：
use_context = false
reset_context = false

你只能输出 JSON，不要输出解释：

{{
  "use_context": true,
  "reset_context": false,
  "reason": "简短原因"
}}
"""

    result = invoke_bedrock_json(prompt)

    return {
        "use_context": bool(result.get("use_context", False)),
        "reset_context": bool(result.get("reset_context", False)),
        "reason": result.get("reason", ""),
    }