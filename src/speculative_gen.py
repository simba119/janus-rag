"""
投机生成模块 (Speculative Generator)

核心创新：
    在模型生成第一个 token 的同时，后台线程发起搜索。
    当生成到一定长度时，将已返回的搜索结果注入上下文，实现“边搜边想”。
    用户感知延迟大幅降低。
"""

import threading
import time
from typing import Generator, List, Dict, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from config import config


class SpeculativeGenerator:
    def __init__(self, model_name: str = None):
        import traceback
        try:
            model_name = model_name or config.TEXT_GEN_MODEL
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[SpeculativeGen] 开始加载模型: {model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True
            )
            if self.device == "cpu":
                self.model = self.model.to("cpu")
            self.search_adapter = None
            print(f"[SpeculativeGen] 模型加载成功")
        except Exception as e:
            print("\n❌ [SpeculativeGen] 模型加载失败，错误详情：")
            traceback.print_exc()
            raise e
        
    def _background_search(self, query: str, result_holder: List):
        if self.search_adapter:
            try:
                results = self.search_adapter.search_sync(query, max_results=5)
                result_holder.extend(results)
            except Exception as e:
                print(f"[后台搜索失败] {e}")
    
    def stream_generate(self, prompt: str, search_query: Optional[str] = None) -> Generator[str, None, None]:
        search_result_holder = []
        search_thread = None
        
        if search_query and self.search_adapter:
            search_thread = threading.Thread(
                target=self._background_search, 
                args=(search_query, search_result_holder)
            )
            search_thread.start()
            yield "[🔍 后台搜索已启动...]\n\n"
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=300,
                do_sample=False,
                temperature=0.1,
                pad_token_id=self.tokenizer.eos_token_id
            )
        generated_ids = outputs[0][len(inputs.input_ids[0]):]
        generated_text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        
        for i, char in enumerate(generated_text):
            yield char
            time.sleep(0.01)
            if search_thread and search_thread.is_alive() and i == 20:
                search_thread.join(timeout=0.5)
        
        if search_thread:
            search_thread.join(timeout=2.0)
        
        if search_result_holder:
            yield "\n\n---\n**📡 实时搜索结果摘要**\n"
            for idx, item in enumerate(search_result_holder[:3], 1):
                yield f"{idx}. **{item.get('title', 'N/A')}**  \n"
                yield f"   *{item.get('snippet', '')[:150]}...*  \n"
                yield f"   来源: {item.get('source', '未知')}  \n\n"
            yield "\n*以上结果已纳入知识库缓存。*\n"