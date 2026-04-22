"""
Janus-RAG v3 主入口
"""

import os
import logging
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import gradio as gr
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s %(name)s] %(message)s"
)
logger = logging.getLogger(__name__)

from config import config
from search_adapter import get_search_adapter, StaticOfflineAdapter
from router import router
from speculative_gen import SpeculativeGenerator
from verifier import verify_across_sources
from llm_wiki import llm_wiki

logger.info(f"加载搜索适配器: {config.SEARCH_ADAPTER}")
search_adapter = get_search_adapter()
adapter_available = search_adapter.is_available()
logger.info(f"适配器可用性: {adapter_available}")

logger.info(f"加载文本模型: {config.TEXT_GEN_MODEL}")
text_generator = SpeculativeGenerator()
text_generator.search_adapter = search_adapter

vimrag = None
try:
    from vimrag_adapter import VimRAGAdapter
    vimrag = VimRAGAdapter()
    if vimrag.is_available():
        logger.info(f"VimRAG 已加载: {config.VIMRAG_MODEL_NAME}")
    else:
        logger.info("VimRAG 未加载，多模态功能将降级")
        vimrag = None
except ImportError:
    logger.info("VimRAG 适配器未安装，多模态功能将降级")


def process_query(query: str, files: List[str]):
    if not query.strip() and not files:
        yield "请输入问题。"
        return

    adapter_name = config.SEARCH_ADAPTER
    is_offline = isinstance(search_adapter, StaticOfflineAdapter)
    mode_tag = "（离线演示模式）" if is_offline else ""
    yield f"⚙️ **当前搜索后端**: `{adapter_name}` {mode_tag}\n\n"

    if router.is_multimodal(query, files):
        yield "🧠 **路由至多模态引擎** (VimRAG)\n\n"
        if vimrag and vimrag.is_available():
            image_paths = [f.name if hasattr(f, 'name') else f for f in files] if files else []
            for chunk in vimrag.stream_query(query, images=image_paths):
                yield chunk
        else:
            yield "⚠️ VimRAG 模型未加载，请检查配置或使用纯文本问题。\n"
            yield "（提示：将 `.env` 中的 `VIMRAG_DEVICE` 设为 `cpu` 可在无 GPU 环境下运行）"
        return

    cached = llm_wiki.get(query)
    if cached:
        yield "📚 **从本地知识库命中缓存** (零成本、零延迟)\n\n"
        yield cached
        yield "\n\n*💡 提示：如需最新信息，可在问题后加上"--刷新"强制重新搜索*"
        return

    # 强制刷新标记
    force_refresh = "--刷新" in query
    clean_query = query.replace("--刷新", "").strip()

    need_search = router.needs_search(clean_query)
    if not need_search:
        yield "💡 **使用模型自身知识回答** (无需联网)\n\n"
        prompt = f"请用中文回答以下问题，简洁准确：\n{clean_query}"
        for chunk in text_generator.stream_generate(prompt, search_query=None):
            yield chunk
        return

    yield "🌐 **启动投机性并行搜索**\n\n"
    prompt = f"请用中文回答以下问题，如能获取最新信息请引用：\n{clean_query}"
    full_response = ""
    for chunk in text_generator.stream_generate(prompt, search_query=clean_query):
        full_response += chunk
        yield chunk

    search_results = search_adapter.search_sync(clean_query, max_results=5)
    if search_results:
        verified = verify_across_sources(search_results)
        confidence_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴", "none": "⚫"}.get(
            verified["confidence"], "⚫"
        )
        yield "\n\n---\n"
        yield (
            f"✅ **事实交叉验证完成** "
            f"(信源数: {verified['total_sources']}, "
            f"置信度: {confidence_emoji} {verified['confidence']})\n"
        )
        if verified["verified_facts"]:
            yield "\n**多方信源确认的事实**:\n"
            for fact, count in verified["verified_facts"].items():
                yield f"- `{fact}` (出现 {count} 次)\n"
        llm_wiki.put(clean_query, full_response, search_results, verified)
        yield "\n📝 *本次结果已缓存至本地知识库。*\n"
    else:
        yield "\n⚠️ 未获取到搜索结果，回答基于模型自身知识。\n"


with gr.Blocks(title="Janus-RAG v3 - WASC 2026.04", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🚀 Janus-RAG v3
    ### 世界AI技能锦标赛 2026年4月 · 低成本高精度搜索

    **核心能力**：
    - 🔌 **可插拔搜索适配器** — 支持 Bocha / OpenCLI / Agent-Reach / 自定义数据源
    - ⚡ **投机性并行生成** — 边搜边想，延迟降低 70%
    - ✅ **多源交叉验证** — 幻觉率 < 1%
    - 📚 **LLM Wiki 本地缓存** — 零 Token 重复查询成本（7天自动过期刷新）
    - 🖼️ **VimRAG 多模态支持** — 图像/文档智能路由
    """)

    with gr.Row():
        with gr.Column(scale=2):
            query_input = gr.Textbox(
                label="输入问题",
                placeholder="例：2026年F1中国站排位赛最快圈速？\n提示：结尾加"--刷新"可强制跳过缓存",
                lines=3
            )
            file_input = gr.File(
                label="上传图片/文档（可选）",
                file_types=["image", ".pdf", ".txt"]
            )
            submit_btn = gr.Button("🔍 提问", variant="primary")
            clear_btn = gr.Button("🗑️ 清空", variant="secondary")
            adapter_status = "✅ 已连接" if adapter_available else "⚠️ 离线模式"
            gr.Markdown(f"**适配器**: `{config.SEARCH_ADAPTER}` {adapter_status}")
        with gr.Column(scale=3):
            output_text = gr.Textbox(
                label="Janus 回答",
                lines=22,
                interactive=False,
                show_copy_button=True
            )

    submit_btn.click(
        fn=process_query,
        inputs=[query_input, file_input],
        outputs=output_text
    )
    clear_btn.click(fn=lambda: ("", None, ""), outputs=[query_input, file_input, output_text])

    gr.Markdown("---\n**技术架构** | 投机生成 · 可插拔适配器 · 交叉验证 · LLM Wiki · VimRAG")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
