import json

from app.graph import build_graph


def main():
    graph = build_graph()

    initial_state = {
        "question": "统计 2026-05-14 新增用户的用户等级分布",
        "request_id": "langgraph-multitask-test-001",
    }

    result = graph.invoke(initial_state)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()