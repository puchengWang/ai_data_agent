import json

from app.graph import build_graph


def main():
    graph = build_graph()

    initial_state = {
        "session_id": "test-session-001",
        "question": "2026-05-21新增用户量是多少",
        "request_id": "session-test-002",
    }

    result = graph.invoke(initial_state)

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()


"""
    initial_state = {
        "session_id": "test-session-001",
        "question": "哪个等级下降最多？",
        "request_id": "session-test-002",
    }


    initial_state = {
        "session_id": "test-session-001",
        "question": "统计 2026-05-08 到 2026-05-14 各用户等级新增用户数趋势",
        "request_id": "session-test-001",
    }
"""    