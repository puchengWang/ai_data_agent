import json

from app.graph import build_graph


def main():
    graph = build_graph()

    initial_state = {
        "question": "统计2026-05-13到2026-05-14的用户有多少？",
        "request_id": "langgraph-semantic-test-001",
    }

    result = graph.invoke(initial_state)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()