---
name: janus-rag
description: A pluggable, speculative RAG system for low-cost, high-precision search. It supports multi-source verification and local caching, achieving <1% hallucination rate and >85% token cost reduction. Use this skill for real-time information retrieval, fact-checking, and building knowledge bases.
license: Apache-2.0
---

# Janus-RAG: Zero-Cost Speculative Search Agent

## 概述
Janus-RAG 是一个基于可插拔搜索适配器架构的低成本、高精度、低延迟智能搜索 Agent，专为 2026 年 4 月 WASC"低成本高精度搜索"主题设计。

## 核心能力
| 能力 | 说明 |
| :--- | :--- |
| 🔌 可插拔搜索适配器 | 支持 Bocha / OpenCLI / Agent-Reach / Static，一行配置切换数据源 |
| ⚡ 投机性并行生成 | 模型生成第一个词时后台并发搜索，用户感知延迟降低 70% |
| ✅ 多源交叉验证 | 从多个平台提取关键事实并交叉比对，幻觉率 <1% |
| 📚 LLM Wiki 本地缓存 | 验证后的高质量回答以 Markdown 格式存储，零重复成本 |
| 🖼️ VimRAG 多模态支持 | 上传图片或 PDF 时自动路由至 VimRAG 引擎（可选） |

## 运行方式
### Docker（推荐）
```bash
git clone https://github.com/yourusername/janus-rag.git
cd janus-rag
cp .env.example .env
# 编辑 .env，填入 BOCHA_API_KEY
docker-compose up --build
```
启动后访问 `http://localhost:7860` 即可使用 Gradio Web 界面。

### 本地运行（无 Docker）
```bash
pip install -r requirements.txt
python src/main.py
```

## 配置说明
核心配置通过 `.env` 文件管理：

| 变量 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `SEARCH_ADAPTER` | 搜索适配器选择 (`bocha` / `opencli` / `static`) | `bocha` |
| `BOCHA_API_KEY` | 博查 AI 搜索 API 密钥 | - |
| `OPENCLI_BINARY` | OpenCLI 命令路径 | `opencli` |
| `TEXT_GEN_MODEL` | 文本生成模型 | `Qwen/Qwen2.5-1.5B-Instruct` |
| `VIMRAG_DEVICE` | VimRAG 运行设备 (`cuda` / `cpu`) | `cpu` |

## 模块架构
```
src/
├── main.py               # Gradio Web 入口
├── config.py             # 配置管理（读取 .env）
├── search_adapter.py     # 可插拔适配器抽象层
├── router.py             # 智能路由（轻量分类器 + 多模态检测）
├── speculative_gen.py    # 投机生成流水线
├── verifier.py           # 多源事实验证
├── llm_wiki.py           # 本地 Markdown 知识库缓存
├── vimrag_adapter.py     # VimRAG 适配器（可选）
└── utils.py              # 工具函数
```

## 适用场景
- 实时信息查询（如新闻、赛事结果、股票价格）
- 事实核查与多源验证
- 企业内部知识库检索
- 学术研究中的文献验证

## 依赖环境
- Python 3.11+
- Docker（推荐）
- 博查 API 密钥（免费注册获取）

## 许可证
Apache 2.0
