"""
事实验证模块 (Fact Verifier)

改进：
    - 增加英文数字/实体模式
    - 空列表输入不崩溃
    - 置信度逻辑更细分（high/medium/low/none）
"""

from collections import Counter
import re
from typing import Dict, List


def extract_facts(text: str) -> List[str]:
    if not text:
        return []
    facts = []
    patterns = [
        r'\d+(?:\.\d+)?\s*(?:亿|万|%|美元|元|人|次|°C|秒|分|圈|kg|km|ms)',
        r'\d{4}年\d{1,2}月\d{1,2}日',
        r'[1-9]\d{0,2}\s*(?:岁|公里|米|千克)',
        r'\d+\.\d+\s*(?:seconds?|minutes?|GHz|MB|GB|TB)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        facts.extend(matches)
    return facts


def verify_across_sources(search_results: List[Dict]) -> Dict:
    if not search_results:
        return {
            "verified_facts": {},
            "total_sources": 0,
            "confidence": "none",
            "sources": []
        }

    all_snippets = [item.get("snippet", "") for item in search_results]
    all_facts = []
    for snippet in all_snippets:
        all_facts.extend(extract_facts(snippet))

    freq = Counter(all_facts)
    verified = {fact: count for fact, count in freq.items() if count >= 2}

    total_sources = len(search_results)
    verified_count = len(verified)

    if verified_count >= 3:
        confidence = "high"
    elif verified_count >= 1:
        confidence = "medium"
    elif total_sources >= 2:
        confidence = "low"
    else:
        confidence = "none"

    return {
        "verified_facts": verified,
        "total_sources": total_sources,
        "confidence": confidence,
        "sources": search_results
    }
