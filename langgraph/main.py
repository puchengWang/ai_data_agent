import json

from app.graph import build_graph


def main():
    graph = build_graph()

    initial_state = {
        "question": "统计截止2026-05-14的用户总数有多少？5月14日新增了多少用户？5月14日新增用户数是否大于5月13日？",
        "request_id": "langgraph-multitask-test-001",
    }

    result = graph.invoke(initial_state)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()