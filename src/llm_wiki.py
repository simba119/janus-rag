"""
LLM Wiki 模块 (本地结构化知识库缓存)

设计理念：
    替代复杂的向量数据库。让 LLM 自己维护一个人类可读的 Markdown 知识库。
    每次搜索验证后的高质量回答会写入本地文件，下次相同查询直接读取，零 Token 成本。
"""

import os
import re
import hashlib
from datetime import datetime
from typing import Optional, Dict, List
from config import config


class LLMWiki:
    def __init__(self, storage_dir: str = None):
        self.storage_dir = storage_dir or config.LLM_WIKI_DIR
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def _slugify(self, text: str) -> str:
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        text = re.sub(r'\s+', '_', text.strip())
        if len(text) > 50:
            text = text[:50]
        return text
    
    def _get_filepath(self, query: str) -> str:
        slug = self._slugify(query)
        hash_suffix = hashlib.md5(query.encode()).hexdigest()[:6]
        filename = f"{slug}_{hash_suffix}.md"
        return os.path.join(self.storage_dir, filename)
    
    def get(self, query: str) -> Optional[str]:
        filepath = self._get_filepath(query)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if '---' in content:
                    parts = content.split('---')
                    if len(parts) >= 3:
                        return parts[2].strip()
                return content.strip()
        return None
    
    def put(self, query: str, answer: str, sources: List[Dict] = None, verified: Dict = None):
        filepath = self._get_filepath(query)
        metadata = f"""---
query: {query}
timestamp: {datetime.now().isoformat()}
verified_confidence: {verified.get('confidence', 'N/A') if verified else 'N/A'}
sources: {len(sources) if sources else 0}
---

"""
        content = metadata + answer
        if sources:
            content += "\n\n## 参考信源\n"
            for i, src in enumerate(sources, 1):
                content += f"{i}. **{src.get('title', 'N/A')}**  \n"
                content += f"   {src.get('link', '#')}  \n"
                content += f"   *{src.get('snippet', '')[:200]}...*  \n\n"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def list_entries(self) -> List[str]:
        return [f for f in os.listdir(self.storage_dir) if f.endswith('.md')]


llm_wiki = LLMWiki()