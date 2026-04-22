"""
投机生成模块 (Speculative Generator)

改进：
    - 懒加载模型，加载失败时降级为搜索摘要模式
    - temperature 参数仅在 do_sample=True 时传入（修复 transformers 警告）
    - time.sleep 改为字符批量输出，提升流式体验
    - 增加 OOM 捕获
"""

import threading
import time
import logging
from typing import Generator, List, Dict, Optional
from config import config

logger = logging.getLogger(__name__)


class SpeculativeGenerator:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.TEXT_GEN_MODEL
        self.search_adapter = None
        self._model = None
        self._tokenizer = None
        self._load_failed = False
        self._load_model()

    def _load_model(self):
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, trust_remote_code=True
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True
            )
            if self.device == "cpu":
                self._model = self._model.to("cpu")
            logger.info(f"[Generator] 模型加载成功: {self.model_name} on {self.device}")
        except Exception as e:
            logger.warning(f"[Generator] 模型加载失败，将使用搜索摘要兜底: {e}")
            self._load_failed = True

    def _background_search(self, query: str, result_holder: List):
        if self.search_adapter:
            try:
                results = self.search_adapter.search_sync(query, max_results=5)
                result_holder.extend(results)
            except Exception as e:
                logger.warning(f"[后台搜索失败] {e}")

    def _fallback_generate(self, search_results: List[Dict]) -> str:
        """模型不可用时，直接用搜索结果拼装回答"""
        if not search_results:
            return "⚠️ 模型未加载且无搜索结果，请检查环境配置。"
        lines = ["**基于搜索结果的摘要回答**（模型未加载）\n"]
        for i, item in enumerate(search_results[:3], 1):
            lines.append(f"**{i}. {item.get('title', '')}**")
            lines.append(item.get('snippet', '')[:300])
            lines.append(f"来源: {item.get('link', '')}\n")
        return "\n".join(lines)

    def stream_generate(self, prompt: str, search_query: Optional[str] = None) -> Generator[str, None, None]:
        import torch
        search_result_holder = []
        search_thread = None

        if search_query and self.search_adapter:
            search_thread = threading.Thread(
                target=self._background_search,
                args=(search_query, search_result_holder)
            )
            search_thread.start()
            yield "[🔍 后台搜索已启动...]\n\n"

        if self._load_failed or self._model is None:
            if search_thread:
                search_thread.join(timeout=5.0)
            fallback = self._fallback_generate(search_result_holder)
            yield fallback
            return

        try:
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=300,
                    do_sample=False,
                    pad_token_id=self._tokenizer.eos_token_id
                )
            generated_ids = outputs[0][len(inputs.input_ids[0]):]
            generated_text = self._tokenizer.decode(generated_ids, skip_special_tokens=True)

            # 批量输出字符，每批 5 个，减少 yield 次数
            BATCH = 5
            for i in range(0, len(generated_text), BATCH):
                yield generated_text[i:i + BATCH]
                time.sleep(0.02)
                if search_thread and search_thread.is_alive() and i == 20:
                    search_thread.join(timeout=0.5)

        except torch.cuda.OutOfMemoryError:
            yield "\n\n⚠️ GPU 显存不足，请将 VIMRAG_DEVICE 设为 cpu 后重试。\n"
        except Exception as e:
            logger.error(f"[Generator] 生成失败: {e}")
            yield f"\n\n⚠️ 生成出错: {str(e)}\n"

        if search_thread:
            search_thread.join(timeout=2.0)

        if search_result_holder:
            yield "\n\n---\n**📡 实时搜索结果摘要**\n"
            for idx, item in enumerate(search_result_holder[:3], 1):
                title = item.get('title', 'N/A')
                snippet = item.get('snippet', '')[:150]
                source = item.get('source', '未知')
                yield f"{idx}. **{title}**  \n   *{snippet}...*  \n   来源: {source}  \n\n"
            yield "\n*以上结果已纳入知识库缓存。*\n"
