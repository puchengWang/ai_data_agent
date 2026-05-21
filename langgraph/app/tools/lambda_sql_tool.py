import json
import boto3
from typing import Any, Dict

from app.config import AWS_REGION, SQL_EXECUTOR_LAMBDA_NAME


lambda_client = boto3.client("lambda", region_name=AWS_REGION)


def invoke_sql_executor(
    intent: str,
    params: Dict[str, Any],
    request_id: str = "langgraph-local-test-001",
) -> Dict[str, Any]:
    # 调用 SQL Executor Lambda。
    # 输入协议：
    # {
    #   "intent": "count_users_by_atime",
    #   "params": {
    #     "start_time": "2026-05-19",
    #     "end_time": "2026-05-20"
    #   },
    #   "request_id": "xxx"
    # }

    payload = {
        "intent": intent,
        "params": params,
        "request_id": request_id,
    }

    response = lambda_client.invoke(
        FunctionName=SQL_EXECUTOR_LAMBDA_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )

    raw_payload = response["Payload"].read().decode("utf-8")

    try:
        result = json.loads(raw_payload)
    except json.JSONDecodeError:
        return {
            "success": False,
            "intent": intent,
            "data": None,
            "error": f"Lambda returned non-json payload: {raw_payload}",
            "meta": {
                "source": "lambda",
                "lambda_name": SQL_EXECUTOR_LAMBDA_NAME,
            },
        }

    if response.get("FunctionError"):
        return {
            "success": False,
            "intent": intent,
            "data": None,
            "error": result,
            "meta": {
                "source": "lambda",
                "lambda_name": SQL_EXECUTOR_LAMBDA_NAME,
            },
        }

    return result


def invoke_sql_executor_with_query_plan(
    query_plan: Dict[str, Any],
    request_id: str = "langgraph-semantic-test-001",
) -> Dict[str, Any]:

    payload = {
        "query_plan": query_plan,
        "request_id": request_id,
    }

    response = lambda_client.invoke(
        FunctionName=SQL_EXECUTOR_LAMBDA_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )

    raw_payload = response["Payload"].read().decode("utf-8")

    try:
        result = json.loads(raw_payload)
    except json.JSONDecodeError:
        return {
            "success": False,
            "data": None,
            "error": f"Lambda returned non-json payload: {raw_payload}",
        }

    if response.get("FunctionError"):
        return {
            "success": False,
            "data": None,
            "error": result,
        }

    return result