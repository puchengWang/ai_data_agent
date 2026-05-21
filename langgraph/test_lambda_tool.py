import json

from app.tools.lambda_sql_tool import invoke_sql_executor


def main():
    result = invoke_sql_executor(
        intent="count_users_by_atime",
        params={
            "start_time": "2026-05-19",
            "end_time": "2026-05-20",
        },
        request_id="lambda-tool-test-001",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
