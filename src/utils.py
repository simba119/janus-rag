"""
工具函数模块
"""

import json
from typing import List, Dict


def format_as_markdown_table(data: List[Dict], columns: List[str] = None) -> str:
    if not data:
        return "*无数据*"
    if columns is None:
        columns = list(data[0].keys())
    header = "| " + " | ".join(columns) + " |\n"
    separator = "|" + "|".join([" --- " for _ in columns]) + "|\n"
    rows = ""
    for item in data:
        row = "| " + " | ".join(str(item.get(col, "")) for col in columns) + " |\n"
        rows += row
    return header + separator + rows


def export_to_json(data: Dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def truncate_text(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."