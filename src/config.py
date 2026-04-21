"""
配置管理模块
所有配置项优先从环境变量读取，其次使用默认值。
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ========== 核心：可插拔搜索适配器 ==========
    SEARCH_ADAPTER = os.getenv("SEARCH_ADAPTER", "bocha")
    
    # ========== 博查 Web Search API ==========
    BOCHA_API_KEY = os.getenv("BOCHA_API_KEY", "")
    
    # ========== OpenCLI 配置 ==========
    OPENCLI_BINARY = os.getenv("OPENCLI_BINARY", "opencli")
    
    # ========== 模型配置（可切换测试用模型） ==========
    TEXT_GEN_MODEL = os.getenv("TEXT_GEN_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
    VIMRAG_DEVICE = os.getenv("VIMRAG_DEVICE", "cpu")
    
    # ========== 路由与超时 ==========
    TEXT_SEARCH_CONFIDENCE_THRESHOLD = float(os.getenv("SEARCH_THRESHOLD", "0.7"))
    SEARCH_TIMEOUT = float(os.getenv("SEARCH_TIMEOUT", "1.5"))
    
    # ========== LLM Wiki 缓存目录 ==========
    LLM_WIKI_DIR = os.getenv("LLM_WIKI_DIR", "./llm_wiki_data")

config = Config()