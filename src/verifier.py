"""
事实验证模块 (Fact Verifier)
"""

from collections import Counter
import re
from typing import Dict, List


def extract_facts(text: str) -> List[str]:
    facts = []
    # 数字 + 常见单位
    patterns = [
        r'\d+(?:\.\d+)?\s*(?:亿|万|%|美元|元|人|次|°C|秒|分|圈|公里|米|千克|岁)',
        r'\d{4}年\d{1,2}月\d{1,2}日',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        facts.extend(matches)
    
    # 简单提取中文专有名词（连续两个以上中文字符，且包含常见后缀）
    # 如：维斯塔潘、上海国际赛车场、红牛车队
    proper_nouns = re.findall(r'[A-Z][a-z]+(?:[-\s][A-Z][a-z]+)*|[\u4e00-\u9fff]{2,}(?:车队|公司|集团|大学|学院|医院|中心|组织|协会|委员会|大奖赛|赛车场)?', text)
    # 去重并过滤过短的结果
    for noun in set(proper_nouns):
        if len(noun) >= 3 and not noun.isdigit():
            facts.append(noun)
    
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