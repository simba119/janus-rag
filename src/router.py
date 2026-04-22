"""
智能路由模块 (Intelligent Router)

改进：
    - 懒加载模型（import 时不加载，首次调用时才加载）
    - 加载失败时降级为关键词规则路由，不崩溃
    - 多模态关键词扩充
"""

import logging
from config import config

logger = logging.getLogger(__name__)


class SmartRouter:
    def __init__(self):
        self._classifier = None
        self._classifier_failed = False
        self.labels = ["需要实时信息", "需要常识或静态知识"]

    def _load_classifier(self):
        """懒加载：首次调用时才下载模型"""
        if self._classifier is not None or self._classifier_failed:
            return
        try:
            from transformers import pipeline
            self._classifier = pipeline(
                "zero-shot-classification",
                model="MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33",
                device=-1
            )
            logger.info("[Router] 零样本分类器加载成功")
        except Exception as e:
            logger.warning(f"[Router] 分类器加载失败，降级为关键词路由: {e}")
            self._classifier_failed = True

    def _keyword_needs_search(self, query: str) -> bool:
        """规则兜底：分类器不可用时使用"""
        realtime_keywords = [
            "最新", "今天", "现在", "当前", "2024", "2025", "2026",
            "今年", "本周", "昨天", "刚刚", "最近", "新闻", "价格",
            "股价", "天气", "比分", "排名", "发布", "上市", "latest"
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in realtime_keywords)

    def needs_search(self, query: str) -> bool:
        self._load_classifier()
        if self._classifier_failed or self._classifier is None:
            return self._keyword_needs_search(query)
        try:
            result = self._classifier(query, self.labels)
            label = result["labels"][0]
            score = result["scores"][0]
            return label == "需要实时信息" and score > config.TEXT_SEARCH_CONFIDENCE_THRESHOLD
        except Exception as e:
            logger.warning(f"[Router] 分类推理失败，降级关键词路由: {e}")
            return self._keyword_needs_search(query)

    @staticmethod
    def is_multimodal(query: str, files: list) -> bool:
        if files:
            return True
        multimodal_keywords = [
            "图片", "照片", "图像", "视频", "截图", "这个图", "这张图",
            "图中", "图上", "如图", "附图", "picture", "image", "photo",
            "video", "看图", "识别", "分析图", "文档", "pdf"
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in multimodal_keywords)


router = SmartRouter()
