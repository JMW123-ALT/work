# 项目架构

当前项目采用单后端、单端口、单数据目录。

```text
frontend
  -> /api/chat        文创 Agent
  -> /api/ask         RAG 问答
  -> /api/search      语义检索
  -> /api/ingest      资料入库

backend/app
  -> api/v1           FastAPI 路由
  -> services/agent   LangGraph 文创 Agent 工作流
  -> services/rag     检索、重排、问答编排
  -> services/vector_store
                      SQLite 元数据 + Chroma 向量库
  -> services/llm_client
                      OpenAI SDK + DeepSeek 调用入口
```

## 运行方式

统一启动一个后端服务：

```powershell
.\run.ps1
```

默认地址：

```text
http://127.0.0.1:8000/api/docs
```

## 数据目录

入库、检索、RAG 和文创 Agent 共用同一套本地数据：

```text
backend/data/vector_store.sqlite3
backend/data/chroma/
backend/data/uploads/
```

同事更新入库数据后，只要这些目录和集合保持一致，文创 Agent 会通过内部 `rag_service` 直接使用，不再走第二个 Agent 服务或 HTTP 检索适配器。

## 验证

最小链路 smoke：

```powershell
cd backend
..\.venv\Scripts\python.exe scripts\smoke_agent.py
```
