# Wenchuang Agent Backend

单后端、单端口、单数据目录的文创 Agent 项目。

## Run

```powershell
.\run.ps1
```

默认服务：

```text
http://127.0.0.1:8000/api/docs
```

## Main APIs

- `POST /api/chat`：文创 Agent
- `POST /api/ask`：RAG 问答
- `POST /api/search`：语义检索
- `POST /api/ingest`：资料入库

## Shared Data

```text
backend/data/vector_store.sqlite3
backend/data/chroma/
backend/data/uploads/
```
