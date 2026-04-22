"""
LLM Wiki 模块 (本地结构化知识库缓存)

改进：
    - get() 增加过期检查（默认 7 天，可配置）
    - put() 写文件原子化（先写临时文件再 rename，防止写一半崩溃）
    - list_entries() 返回带元数据的结构，方便管理
"""

import os
import re
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from config import config

logger = logging.getLogger(__name__)

CACHE_TTL_DAYS = int(os.getenv("WIKI_CACHE_TTL_DAYS", "7"))


class LLMWiki:
    def __init__(self, storage_dir: str = None):
        self.storage_dir = storage_dir or config.LLM_WIKI_DIR
        os.makedirs(self.storage_dir, exist_ok=True)

    def _slugify(self, text: str) -> str:
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        text = re.sub(r'\s+', '_', text.strip())
        return text[:50] if len(text) > 50 else text

    def _get_filepath(self, query: str) -> str:
        slug = self._slugify(query)
        hash_suffix = hashlib.md5(query.encode()).hexdigest()[:6]
        return os.path.join(self.storage_dir, f"{slug}_{hash_suffix}.md")

    def _is_expired(self, filepath: str) -> bool:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            match = re.search(r'timestamp:\s*(.+)', content)
            if not match:
                return False
            ts = datetime.fromisoformat(match.group(1).strip())
            return datetime.now() - ts > timedelta(days=CACHE_TTL_DAYS)
        except Exception:
            return False

    def get(self, query: str) -> Optional[str]:
        filepath = self._get_filepath(query)
        if not os.path.exists(filepath):
            return None
        if self._is_expired(filepath):
            logger.info(f"[LLMWiki] 缓存过期，重新查询: {query[:30]}")
            os.remove(filepath)
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            if '---' in content:
                parts = content.split('---')
                if len(parts) >= 3:
                    return parts[2].strip()
            return content.strip()
        except Exception as e:
            logger.warning(f"[LLMWiki] 读取缓存失败: {e}")
            return None

    def put(self, query: str, answer: str, sources: List[Dict] = None, verified: Dict = None):
        filepath = self._get_filepath(query)
        tmp_path = filepath + ".tmp"
        metadata = (
            f"---\n"
            f"query: {query}\n"
            f"timestamp: {datetime.now().isoformat()}\n"
            f"verified_confidence: {verified.get('confidence', 'N/A') if verified else 'N/A'}\n"
            f"sources: {len(sources) if sources else 0}\n"
            f"---\n\n"
        )
        content = metadata + answer
        if sources:
            content += "\n\n## 参考信源\n"
            for i, src in enumerate(sources, 1):
                content += f"{i}. **{src.get('title', 'N/A')}**  \n"
                content += f"   {src.get('link', '#')}  \n"
                content += f"   *{src.get('snippet', '')[:200]}...*  \n\n"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            os.replace(tmp_path, filepath)
        except Exception as e:
            logger.error(f"[LLMWiki] 写入缓存失败: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def list_entries(self) -> List[Dict]:
        entries = []
        for fname in os.listdir(self.storage_dir):
            if fname.endswith('.md'):
                fpath = os.path.join(self.storage_dir, fname)
                size = os.path.getsize(fpath)
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat()
                entries.append({"file": fname, "size_bytes": size, "modified": mtime})
        return sorted(entries, key=lambda x: x["modified"], reverse=True)


llm_wiki = LLMWiki()
