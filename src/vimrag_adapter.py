"""
VimRAG 适配器（可选模块）
当前已主动禁用，跳过模型加载，所有调用将优雅降级。
"""

from typing import List, Union, Generator


class VimRAGAdapter:
    def __init__(self):
        self.model = None
        self.processor = None
        print("[VimRAG] 已主动禁用，跳过模型加载。")
    
    def is_available(self) -> bool:
        return False
    
    def query(self, prompt: str, images: List[Union[str, "Image.Image"]] = None) -> str:
        return "[VimRAG 不可用]"
    
    def stream_query(self, prompt: str, images: List[Union[str, "Image.Image"]] = None) -> Generator[str, None, None]:
        yield "[VimRAG 不可用]"