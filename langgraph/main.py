import json

from app.graph import build_graph


def main():
    graph = build_graph()

    initial_state = {
        "question": "统计 2026-05-08 到 2026-05-14 每天新增用户趋势",
        "request_id": "langgraph-multitask-test-001",
    }

    result = graph.invoke(initial_state)

#    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(
        f"  {status} | aggregation_type={result['actual_aggregation_type']} "
        f"| operators={result.get('actual_operators')} "
        f"| duration={result['duration_ms']}ms"
    )

if __name__ == "__main__":
    main()