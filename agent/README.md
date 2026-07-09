# 文创 Agent

这是文创智能体子工程。完整项目运行时，它通过 `../backend/` 的 `/api/v1/search` 使用 `backend/data` 中已有的 SQLite/Chroma 数据。

## 已完成能力

- 统一 LLM 调用封装，兼容 DeepSeek/OpenAI 风格接口，并支持 streaming。
- LangGraph 主流程：需求解析 -> 知识检索 -> 文化考据 -> 创意设计 -> 营销文案。
- Mock 本地知识库，便于没有真实 Chroma 时继续开发。
- Chroma 检索适配器，支持 `source_id`、`object_type`、`title`、`section_path`、`permission_level` 等元数据映射。
- qwen3-vl-embedding 和 qwen3-rerank 客户端封装。
- Pydantic 状态结构体 `Evidence`、`WenchuangState`。
- FastAPI 接口：普通问答、流式问答、流程查看、演示案例。

## 配置

优先读取 `agent/.env`，也会读取上一级 `../.env`。推荐团队联调时使用根目录 `../.env`，个人临时配置可以放在 `agent/.env`。

示例：

```text
LLM_API_KEY=你的 DeepSeek Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash

EMBEDDING_API_KEY=你的 qwen3-vl-embedding Key
EMBEDDING_DASHSCOPE_URL=https://ws-n81tu3iqo4jsalm2.cn-beijing.maas.aliyuncs.com/api/v1
EMBEDDING_MODEL=qwen3-vl-embedding

RERANK_API_KEY=你的 qwen3-rerank Key
RERANK_BASE_URL=https://ws-n81tu3iqo4jsalm2.cn-beijing.maas.aliyuncs.com/api/v1
RERANK_MODEL=qwen3-rerank
RERANK_ENABLED=false

RETRIEVER_PROVIDER=shujuku
SHUJUKU_SEARCH_URL=http://127.0.0.1:8001/api/v1/search
SHUJUKU_USER_TYPE=visitor

CHROMA_PATH=../backend/data/chroma
CHROMA_COLLECTION=tourism_knowledge_vectors
MIN_RETRIEVAL_CONFIDENCE=0.7
```

不配置 API Key 时会走 Mock 输出，方便先验证流程。

## 安装依赖

建议在本目录单独建环境，不要和 `../backend/` 共用同一个 `.venv`。后端当前依赖较旧的 LangChain 组件，Agent/LangGraph 依赖较新版本，混装容易冲突。

```powershell
cd D:\User\work\shujuku\agent
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 命令行运行

```powershell
cd D:\User\work\shujuku\agent
.\.venv\Scripts\python.exe wenchuang_agent.py "敦煌保温杯文创，偏国潮厚重风，输出小红书文案"
```

演示脚本：

```powershell
.\.venv\Scripts\python.exe scripts\run_demo.py "敦煌保温杯文创，偏国潮厚重风"
```

## API 服务

```powershell
cd D:\User\work\shujuku\agent
.\.venv\Scripts\python.exe -m uvicorn wc_agent.api:app --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000/docs
```

健康检查：

```powershell
curl http://127.0.0.1:8000/health
```

调用 Agent：

```powershell
curl -X POST http://127.0.0.1:8000/chat `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"敦煌保温杯文创，偏国潮厚重风，输出小红书文案\"}"
```

流式输出：

```powershell
curl -X POST http://127.0.0.1:8000/chat/stream `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"敦煌保温杯文创，偏国潮厚重风，输出小红书文案\"}"
```

## 测试

```powershell
cd D:\User\work\shujuku\agent
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 后续接知识库

当前有两个检索实现：

- `MockKnowledgeRetriever`：读取 `wc_agent/data/sample_knowledge.jsonl`。
- `ChromaRetriever`：连接真实 Chroma collection，并按元数据字段转换成 Agent 使用的 `Evidence`。
- `ShujukuHttpRetriever`：调用 `../backend/` 的 `/api/v1/search`，这是完整项目默认推荐方式。

完整项目默认使用 `RETRIEVER_PROVIDER=shujuku`。如果只想离线开发 Agent 流程，可以临时改成 `RETRIEVER_PROVIDER=mock`。
