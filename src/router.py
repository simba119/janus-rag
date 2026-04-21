"""
智能路由模块 (Intelligent Router)

功能：
    1. 判断查询是否需要联网搜索（基于零样本分类）
    2. 判断是否为多模态查询（图片/视频/文档）
"""

from transformers import pipeline
from config import config


class SmartRouter:
    def __init__(self):
        self.classifier = pipeline(
            "zero-shot-classification",
            model="MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33",
            device=-1
        )
        self.labels = ["需要实时信息", "需要常识或静态知识"]
        
    def needs_search(self, query: str) -> bool:
        result = self.classifier(query, self.labels)
        label = result["labels"][0]
        score = result["scores"][0]
        if label == "需要实时信息" and score > config.TEXT_SEARCH_CONFIDENCE_THRESHOLD:
            return True
        return False
    
    @staticmethod
    def is_multimodal(query: str, files: list) -> bool:
        if files:
            return True
        multimodal_keywords = [
            "图片", "照片", "图像", "视频", "截图", "这个图", "这张图",
            "图中", "图上", "如图", "附图", "picture", "image", "photo", "video"
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in multimodal_keywords)


router = SmartRouter()