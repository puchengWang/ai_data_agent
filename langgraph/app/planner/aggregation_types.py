AGGREGATION_TYPES = {
    "normal": {
        "description": "基础聚合查询",
        "supported_measures": [
            "count",
            "sum",
            "avg",
            "min",
            "max",
            "distinct_count"
        ]
    },
    "compare": {
        "description": "对比分析"
    },
    "trend": {
        "description": "趋势分析"
    },
    "group_by": {
        "description": "分组统计"
    },
    "top_n": {
        "description": "排名分析"
    },
    "distribution": {
        "description": "分布分析"
    }
}