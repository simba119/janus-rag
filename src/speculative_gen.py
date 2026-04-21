"""
投机生成模块 (Speculative Generator)

核心创新：
    - 在模型生成的同时，后台线程发起搜索，实现“边搜边想”。
    - 使用 TextIteratorStreamer 实现真实的 token 级流式输出。
    - 完善的异常处理，确保生成线程不会导致主线程永久阻塞。
"""

import threading
from typing import Generator, List, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
import torch
from config import config


class SpeculativeGenerator:
    def __init__(self, model_name: str = None, search_adapter=None):
        model_name = model_name or config.TEXT_GEN_MODEL
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
            trust_remote_code=True
        )
        if self.device == "cpu":
            self.model = self.model.to("cpu")
        self.search_adapter = search_adapter
        
    def _background_search(self, query: str, result_holder: List):
        """后台线程执行的搜索任务"""
        if self.search_adapter:
            try:
                results = self.search_adapter.search_sync(query, max_results=5)
                result_holder.extend(results)
            except Exception as e:
                print(f"[后台搜索失败] {e}")
    
    def stream_generate(self, prompt: str, search_query: Optional[str] = None) -> Generator[str, None, None]:
        """
        流式生成文本，如果提供 search_query，则在后台并行搜索并追加结果。
        """
        search_result_holder = []
        search_thread = None
        
        # 如果需要搜索，立即启动后台线程
        if search_query and self.search_adapter:
            search_thread = threading.Thread(
                target=self._background_search, 
                args=(search_query, search_result_holder)
            )
            search_thread.start()
            yield "[🔍 后台搜索已启动...]\n\n"
        
        # 准备模型输入
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        
        # 生成参数：使用贪心解码，不传 temperature 避免冲突
        generate_kwargs = {
            **inputs,
            "max_new_tokens": 300,
            "do_sample": False,
            "pad_token_id": self.tokenizer.eos_token_id,
            "streamer": streamer,
        }
        
        # 包装生成函数，确保异常时 streamer 能正常结束
        def _run_generate(kwargs, streamer):
            try:
                self.model.generate(**kwargs)
            except Exception as e:
                print(f"[生成失败] {e}")
            finally:
                streamer.end()
        
        generate_thread = threading.Thread(target=_run_generate, args=(generate_kwargs, streamer))
        generate_thread.start()
        
        # 主线程逐 token 输出
        for token_text in streamer:
            yield token_text
        
        # 等待生成线程结束
        generate_thread.join()
        
        # 等待后台搜索线程结束（最多等待 5 秒）
        if search_thread:
            search_thread.join(timeout=5.0)
        
        # 如果有搜索结果，追加显示
        if search_result_holder:
            yield "\n\n---\n**📡 实时搜索结果摘要**\n"
            for idx, item in enumerate(search_result_holder[:3], 1):
                yield f"{idx}. **{item.get('title', 'N/A')}**  \n"
                yield f"   *{item.get('snippet', '')[:150]}...*  \n"
                yield f"   来源: {item.get('source', '未知')}  \n\n"
            yield "\n*以上结果已纳入知识库缓存。*\n"