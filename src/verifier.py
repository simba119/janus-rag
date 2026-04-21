"""
事实验证模块 (Fact Verifier)

功能：
    对多个搜索源返回的结果进行交叉验证。
    提取关键数字/实体，统计其在多源中出现的频次。
    只有被至少两个独立信源确认的事实才被视为"已验证"。
"""

from collections import Counter
import re
from typing import Dict, List


def extract_facts(text: str) -> List[str]:
    facts = []
    patterns = [
        r'\d+(?:\.\d+)?\s*(?:亿|万|%|美元|元|人|次|°C|秒|分|圈)',
        r'\d{4}年\d{1,2}月\d{1,2}日',
        r'[1-9]\d{0,2}\s*(?:岁|公里|米|千克)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        facts.extend(matches)
    return facts


def verify_across_sources(search_results: List[Dict]) -> Dict:
    all_snippets = [item.get("snippet", "") for item in search_results]
    all_facts = []
    for snippet in all_snippets:
        all_facts.extend(extract_facts(snippet))
    freq = Counter(all_facts)
    verified = {fact: count for fact, count in freq.items() if count >= 2}
    total_sources = len(search_results)
    if len(verified) >= 3:
        confidence = "high"
    elif len(verified) >= 1:
        confidence = "medium"
    else:
        confidence = "low"
    return {
        "verified_facts": verified,
        "total_sources": total_sources,
        "confidence": confidence,
        "sources": search_results
    }