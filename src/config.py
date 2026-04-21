"""
配置管理模块
所有配置项优先从环境变量读取，其次使用默认值。
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ========== 核心：可插拔搜索适配器 ==========
    # 默认 static（离线演示，开箱即用，无需配置任何 API key）
    # 如需启用博查搜索，请配置 BOCHA_API_KEY 后将 SEARCH_ADAPTER 改为 bocha
    SEARCH_ADAPTER = os.getenv("SEARCH_ADAPTER", "static")
    
    # ========== 博查 API ==========
    BOCHA_API_KEY = os.getenv("BOCHA_API_KEY", "")
    
    # ========== OpenCLI 配置 ==========
    OPENCLI_BINARY = os.getenv("OPENCLI_BINARY", "opencli")
    
    # ========== Agent-Reach 配置 ==========
    AGENT_REACH_ENDPOINT = os.getenv("AGENT_REACH_ENDPOINT", "http://localhost:3000")
    
    # ========== 模型配置 ==========
    TEXT_GEN_MODEL = os.getenv("TEXT_GEN_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
    VIMRAG_MODEL_NAME = os.getenv("VIMRAG_MODEL_NAME", "Qwen/Qwen2-VL-7B-Instruct")
    VIMRAG_DEVICE = os.getenv("VIMRAG_DEVICE", "cpu")
    
    # ========== 路由与超时 ==========
    TEXT_SEARCH_CONFIDENCE_THRESHOLD = float(os.getenv("SEARCH_THRESHOLD", "0.7"))
    SEARCH_TIMEOUT = float(os.getenv("SEARCH_TIMEOUT", "1.5"))
    
    # ========== LLM Wiki 缓存目录 ==========
    LLM_WIKI_DIR = os.getenv("LLM_WIKI_DIR", "./llm_wiki_data")

config = Config()