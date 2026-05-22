import re
from typing import Dict, List, Any


def parse_ddl(ddl: str) -> Dict[str, Any]:
    table_name = extract_table_name(ddl)
    table_comment = extract_table_comment(ddl)
    columns = extract_columns(ddl)
    primary_key = extract_primary_key(ddl)

    return {
        "table_name": table_name,
        "table_comment": table_comment,
        "primary_key": primary_key,
        "columns": columns,
    }


def extract_table_name(ddl: str) -> str:
    match = re.search(
        r"CREATE\s+TABLE\s+`?(\w+)`?",
        ddl,
        re.IGNORECASE
    )

    if not match:
        raise ValueError("Cannot find table name in DDL")

    return match.group(1)


def extract_table_comment(ddl: str) -> str:
    match = re.search(
        r"COMMENT\s*=\s*'([^']*)'",
        ddl,
        re.IGNORECASE
    )

    return match.group(1) if match else ""


def extract_primary_key(ddl: str) -> str:
    match = re.search(
        r"PRIMARY\s+KEY\s*\(`?(\w+)`?\)",
        ddl,
        re.IGNORECASE
    )

    return match.group(1) if match else ""


def extract_columns(ddl: str) -> List[Dict[str, Any]]:
    columns = []

    lines = ddl.splitlines()

    for line in lines:
        line = line.strip().rstrip(",")

        if not line.startswith("`"):
            continue

        match = re.match(
            r"`(?P<name>\w+)`\s+(?P<type>[a-zA-Z0-9()]+).*?(COMMENT\s+'(?P<comment>[^']*)')?",
            line,
            re.IGNORECASE
        )

        if not match:
            continue

        columns.append({
            "name": match.group("name"),
            "type": match.group("type").lower(),
            "comment": match.group("comment") or "",
        })

    return columns