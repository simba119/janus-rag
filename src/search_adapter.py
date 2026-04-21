"""
可插拔搜索适配器模块 (Pluggable Search Adapter)

设计哲学：
    不绑定任何特定搜索脚手架。开发者只需继承 BaseSearchAdapter 并实现三个方法，
    即可将自己的数据源无缝接入 Janus-RAG。

内置适配器：
    - BochaAdapter      : 博查 AI 搜索 API（默认，国内合规，免费额度）
    - OpenCLIAdapter    : 复用浏览器登录态，零成本抓取国内主流平台
    - AgentReachAdapter : 基于 MCP 协议的跨平台 Agent 搜索
    - StaticOfflineAdapter : 离线演示/测试用，从本地 JSON 读取

自定义适配器：
    1. 新建一个类，继承 BaseSearchAdapter
    2. 实现 search_sync, search_async, is_available
    3. 在 config.py 中设置 SEARCH_ADAPTER = "你的模块.你的类"
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import subprocess
import json
import asyncio
import os


class BaseSearchAdapter(ABC):
    """搜索适配器抽象基类"""
    
    @abstractmethod
    def search_sync(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """同步搜索，返回标准化结果列表。
        
        每个结果必须包含字段:
            - title   : 标题
            - link    : 原始链接
            - snippet : 内容摘要
            - source  : 来源平台名称
        """
        pass
    
    @abstractmethod
    async def search_async(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """异步搜索接口"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查适配器是否可用"""
        pass


# ============================================================================
# 适配器 0: 博查 AI 搜索 API (默认推荐)
# ============================================================================

class BochaAdapter(BaseSearchAdapter):
    """使用博查 AI 搜索 API。
    
    获取 API Key:
        1. 访问 https://open.bochaai.com 注册
        2. 在控制台获取 API Key
        3. 新用户有 1000 次免费调用额度
    """
    
    def __init__(self, api_key: str = None):
        from config import config
        self.api_key = api_key or config.BOCHA_API_KEY
        self.base_url = "https://api.bocha.cn/v1/web-search"
        self._available = None
        
    def is_available(self) -> bool:
        if self._available is None:
            if not self.api_key:
                self._available = False
            else:
                try:
                    import requests
                    resp = requests.post(
                        self.base_url,
                        json={"query": "test", "count": 1},
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=5
                    )
                    self._available = resp.status_code == 200
                except:
                    self._available = False
        return self._available
    
    def search_sync(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        if not self.is_available():
            return []
        try:
            import requests
            payload = {"query": query, "count": max_results}
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            resp = requests.post(self.base_url, json=payload, headers=headers, timeout=10)
            data = resp.json()
            return self._parse_response(data)
        except:
            return []
    
    async def search_async(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        if not self.is_available():
            return []
        try:
            import aiohttp
            payload = {"query": query, "count": max_results}
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload, headers=headers, timeout=10) as resp:
                    data = await resp.json()
                    return self._parse_response(data)
        except:
            return []
    
    def _parse_response(self, data: dict) -> List[Dict[str, str]]:
        results = []
        # 博查API实际返回结构: data.webPages.value
        web_pages = data.get("data", {}).get("webPages", {})
        items = web_pages.get("value", []) if isinstance(web_pages, dict) else []
        for item in items:
            results.append({
                "title": item.get("name", item.get("title", "")),
                "link": item.get("url", ""),
                "snippet": item.get("snippet", "")[:500],
                "source": "Bocha"
            })
        return results


# ============================================================================
# 适配器 1: OpenCLI
# ============================================================================

class OpenCLIAdapter(BaseSearchAdapter):
    """使用 OpenCLI 命令行工具抓取数据。
    
    替换指南：
        - 修改 __init__ 中的 self.binary 可切换命令路径
        - 修改 platforms 列表可调整搜索的网站
        - 重写 _parse_output 可适配不同输出格式
    """
    
    def __init__(self, binary_path: str = None):
        from config import config
        self.binary = binary_path or config.OPENCLI_BINARY
        self._available = None
        self.platforms = ["zhihu", "bilibili"]
        
    def is_available(self) -> bool:
        if self._available is None:
            try:
                subprocess.run([self.binary, "--version"], capture_output=True, timeout=5)
                self._available = True
            except (subprocess.SubprocessError, FileNotFoundError):
                self._available = False
        return self._available
    
    def search_sync(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        if not self.is_available():
            return []
        all_results = []
        for platform in self.platforms:
            try:
                cmd = [self.binary, platform, "search", query, "--limit", str(max_results)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    parsed = self._parse_output(result.stdout, platform)
                    all_results.extend(parsed[:max_results])
            except subprocess.TimeoutExpired:
                continue
        return all_results
    
    async def search_async(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.search_sync, query, max_results)
    
    def _parse_output(self, raw_output: str, source: str) -> List[Dict[str, str]]:
        try:
            data = json.loads(raw_output)
            results = []
            for item in data.get("items", []):
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("url", ""),
                    "snippet": item.get("description", item.get("content", ""))[:500],
                    "source": source.capitalize()
                })
            return results
        except json.JSONDecodeError:
            return []


# ============================================================================
# 适配器 2: Agent-Reach
# ============================================================================

class AgentReachAdapter(BaseSearchAdapter):
    """Agent-Reach 适配器（预留接口，MCP 协议搜索后端）。

    当前状态：预留接口，尚未接入外部 Agent-Reach 服务。
    如需启用，请部署 Agent-Reach 服务并配置 AGENT_REACH_ENDPOINT。
    未接入时系统自动降级至其他可用适配器。
    """
    
    def __init__(self, endpoint: str = None):
        from config import config
        self.endpoint = endpoint or config.AGENT_REACH_ENDPOINT
        
    def is_available(self) -> bool:
        try:
            import requests
            resp = requests.get(f"{self.endpoint}/health", timeout=2)
            return resp.status_code == 200
        except:
            return False
    
    def search_sync(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        if not self.is_available():
            return []
        try:
            import requests
            resp = requests.post(
                f"{self.endpoint}/search",
                json={"query": query, "max_results": max_results},
                timeout=10
            )
            return self._parse_response(resp.json())
        except:
            return []
    
    async def search_async(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        if not self.is_available():
            return []
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.endpoint}/search",
                    json={"query": query, "max_results": max_results},
                    timeout=10
                ) as resp:
                    return self._parse_response(await resp.json())
        except:
            return []
    
    def _parse_response(self, data: dict) -> List[Dict[str, str]]:
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "link": item.get("url", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("platform", "Agent-Reach")
            })
        return results


# ============================================================================
# 适配器 3: 静态离线适配器
# ============================================================================

class StaticOfflineAdapter(BaseSearchAdapter):
    """从本地 JSON 文件读取预设结果。"""
    
    def __init__(self, data_file: str = "demo/offline_results.json"):
        self.data_file = data_file
        self._cache = None
        
    def _load_cache(self):
        if self._cache is None:
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
            except FileNotFoundError:
                self._cache = {}
        return self._cache
    
    def is_available(self) -> bool:
        return True
    
    def search_sync(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        cache = self._load_cache()
        # 1. 精确关键词匹配（跳过元数据字段）
        for key, results in cache.items():
            if key.startswith("_"):  # 跳过元数据字段
                continue
            if key != "default" and key.lower() in query.lower():
                return results[:max_results]
        # 2. 无匹配时返回 default 兜底数据
        return cache.get("default", [])[:max_results]
    
    async def search_async(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        return self.search_sync(query, max_results)


# ============================================================================
# 适配器工厂
# ============================================================================

def get_search_adapter() -> BaseSearchAdapter:
    """根据配置返回当前激活的搜索适配器实例"""
    from config import config
    
    adapter_name = config.SEARCH_ADAPTER.lower()
    
    if adapter_name == "bocha":
        return BochaAdapter()
    elif adapter_name == "opencli":
        return OpenCLIAdapter()
    elif adapter_name == "agent_reach":
        return AgentReachAdapter()
    elif adapter_name == "static":
        return StaticOfflineAdapter()
    else:
        try:
            import importlib
            module_path, class_name = adapter_name.rsplit(".", 1)
            module = importlib.import_module(module_path)
            adapter_class = getattr(module, class_name)
            return adapter_class()
        except Exception as e:
            raise ValueError(f"无法加载搜索适配器 '{adapter_name}': {e}")