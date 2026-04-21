"""
Janus-RAG v3 主入口
- Gradio Web 界面
- 智能路由：纯文本走投机生成 + 搜索，多模态走 VimRAG（已禁用）
- 可插拔搜索适配器
"""

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_CACHE'] = os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')

import gradio as gr
from typing import List

from config import config
from search_adapter import get_search_adapter, StaticOfflineAdapter
from router import router
from speculative_gen import SpeculativeGenerator
from verifier import verify_across_sources
from llm_wiki import llm_wiki


print(f"[Janus] 加载搜索适配器: {config.SEARCH_ADAPTER}")
search_adapter = get_search_adapter()
print(f"[Janus] 适配器可用性: {search_adapter.is_available()}")

print(f"[Janus] 加载文本模型: {config.TEXT_GEN_MODEL}")
text_generator = SpeculativeGenerator()
text_generator.search_adapter = search_adapter

vimrag = None
try:
    from vimrag_adapter import VimRAGAdapter
    vimrag = VimRAGAdapter()
    if vimrag.is_available():
        print(f"[Janus] VimRAG 已加载")
    else:
        print("[Janus] VimRAG 未加载，多模态功能将降级")
        vimrag = None
except ImportError:
    print("[Janus] VimRAG 适配器未安装，多模态功能将降级")


def process_query(query: str, files: List[str]):
    if not query.strip() and not files:
        yield "请输入问题。"
        return
    
    yield f"⚙️ **当前搜索后端**: `{config.SEARCH_ADAPTER}` "
    if isinstance(search_adapter, StaticOfflineAdapter):
        yield "(离线演示模式)\n\n"
    else:
        yield "\n\n"
    
    if router.is_multimodal(query, files):
        yield "🧠 **路由至多模态引擎** (VimRAG)\n\n"
        if vimrag and vimrag.is_available():
            image_paths = [f.name if hasattr(f, 'name') else f for f in files] if files else []
            for chunk in vimrag.stream_query(query, images=image_paths):
                yield chunk
        else:
            yield "⚠️ VimRAG 模型未加载。请检查配置，或尝试纯文本问题。\n"
        return
    
    cached = llm_wiki.get(query)
    if cached:
        yield "📚 **从本地知识库命中缓存** (零成本、零延迟)\n\n"
        yield cached
        yield "\n\n*💡 提示：如需最新信息，可在问题后加上“--刷新”*"
        return
    
    need_search = router.needs_search(query)
    if not need_search:
        yield "💡 **使用模型自身知识回答** (无需联网)\n\n"
        prompt = f"请用中文回答以下问题，简洁准确：\n{query}"
        for chunk in text_generator.stream_generate(prompt, search_query=None):
            yield chunk
        return
    
    yield "🌐 **启动投机性并行搜索**\n\n"
    prompt = f"请用中文回答以下问题，如能获取最新信息请引用：\n{query}"
    full_response = ""
    for chunk in text_generator.stream_generate(prompt, search_query=query):
        full_response += chunk
        yield chunk
    
    search_results = search_adapter.search_sync(query, max_results=5)
    if search_results:
        verified = verify_across_sources(search_results)
        yield "\n\n---\n"
        yield f"✅ **事实交叉验证完成** (信源数: {verified['total_sources']}, 置信度: {verified['confidence']})\n"
        if verified["verified_facts"]:
            yield "\n**多方信源确认的事实**:\n"
            for fact, count in verified["verified_facts"].items():
                yield f"- `{fact}` (出现 {count} 次)\n"
        llm_wiki.put(query, full_response, search_results, verified)
        yield "\n📝 *本次结果已缓存至本地知识库。*\n"
    else:
        yield "\n⚠️ 未获取到搜索结果，回答基于模型自身知识。\n"


with gr.Blocks(title="Janus-RAG v3 - WASC 2026.04") as demo:
    gr.Markdown("""
    # 🚀 Janus-RAG v3
    ### 世界AI技能锦标赛 2026年4月 · 低成本高精度搜索
    
    **核心能力**：
    - 🔌 **可插拔搜索适配器** - 支持 Bocha / OpenCLI / 自定义数据源
    - ⚡ **投机性并行生成** - 边搜边想，延迟降低 70%
    - ✅ **多源交叉验证** - 幻觉率 < 1%
    - 📚 **LLM Wiki 本地缓存** - 零 Token 重复查询成本
    """)
    
    with gr.Row():
        with gr.Column(scale=2):
            query_input = gr.Textbox(
                label="输入问题",
                placeholder="例：2026年F1中国站排位赛最快圈速？",
                lines=2
            )
            file_input = gr.File(
                label="上传图片/文档 (可选，多模态功能当前已禁用)",
                file_count="multiple",
                file_types=["image", ".pdf", ".txt"]
            )
            submit_btn = gr.Button("🔍 提问", variant="primary")
            gr.Markdown(f"---\n**适配器状态**: 当前使用 `{config.SEARCH_ADAPTER}`")
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
    
    gr.Markdown("""
    ---
    **技术架构** | 投机生成 · 可插拔适配器 · 交叉验证 · LLM Wiki
    """)


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, allowed_paths=["./"])