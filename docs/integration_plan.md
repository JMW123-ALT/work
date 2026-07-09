# 文创 Agent 与知识库联调说明

更新时间：2026-07-09

## 1. 当前整合状态

仓库采用同一个 GitHub repo、两个服务并行运行、一个数据中心的方式：

```text
shujuku/
  backend/   知识库后端，负责入库、权限、检索、审计
  frontend/  知识库前端
  agent/     文创 Agent，负责智能体流程和回答生成
  docs/      双方共享文档
```

`backend/` 是唯一数据中心，继续使用 `backend/data/vector_store.sqlite3` 和 `backend/data/chroma/` 中已有的入库数据。`agent/` 不直接读取数据库，只通过 `POST /api/v1/search` 获取证据。

当前向量模型统一使用 `qwen3-vl-embedding`。如果原来的 Chroma collection 是本地占位向量，需要先运行：

```powershell
.\backend\.venv\Scripts\python.exe backend\scripts\rebuild_chroma.py
```

该命令会保留 SQLite documents，只重建 Chroma 向量索引。

## 2. 推荐运行端口

| 服务 | 目录 | 端口 | 说明 |
|---|---|---:|---|
| 知识库后端 | `backend/` | `8001` | 资料入库、检索、权限、审计 |
| 文创 Agent | `agent/` | `8000` | 文创问答、流式输出、工作流 |
| 前端页面 | `frontend/` | 以后按实际情况 | 可以先调用后端，也可以后续接 Agent |

不要让两个服务都占用 `8000`，否则会互相顶掉。

`backend/` 和 `agent/` 建议各自使用自己的 `.venv`。后端当前固定了较旧的 LangChain 组件，Agent 使用较新的 LangGraph 组件，共用环境会产生依赖冲突。

## 3. 当前运行链路

```text
用户 / Swagger / 前端
-> agent POST /chat
-> ShujukuHttpRetriever
-> backend POST /api/v1/search
-> backend/data/chroma + vector_store.sqlite3
-> Evidence
-> LangGraph 生成文创方案
```

Agent 启动时使用：

```text
RETRIEVER_PROVIDER=shujuku
SHUJUKU_SEARCH_URL=http://127.0.0.1:8001/api/v1/search
```

推荐接口形态：

```text
POST /api/v1/search
```

请求：

```json
{
  "query": "敦煌保温杯文创",
  "top_k": 5,
  "user_type": "visitor",
  "min_confidence": 0.7
}
```

响应：

```json
{
  "items": [
    {
      "text": "chunk 正文内容",
      "source": "shujuku:source-001",
      "category": "culture_doc",
      "culture_theme": "敦煌藻井",
      "confidence": 0.82,
      "copyright_status": "public_domain",
      "risk_level": "low",
      "metadata": {
        "chunk_id": "chunk-001",
        "source_id": "source-001",
        "section_path": "敦煌/藻井",
        "permission_level": "public"
      }
    }
  ]
}
```

## 4. Agent 需要的 Evidence 字段

Agent 最少需要这些字段：

| 字段 | 必填 | 用途 |
|---|---|---|
| `text` | 是 | 文化考据和回答生成的主要依据 |
| `source` | 是 | 回答中的来源追踪 |
| `category` | 建议 | 区分纹样、器物、节庆、策展、合规等资料 |
| `culture_theme` | 建议 | 判断回答主题是否贴合用户需求 |
| `confidence` | 是 | 低于 `0.7` 的结果过滤或降权 |
| `copyright_status` | 建议 | 触发版权复核提示 |
| `risk_level` | 建议 | 触发人工复核或阻断 |

## 5. 代码连接点

Agent 主流程不直接依赖 Chroma 或 SQLite，只依赖检索器协议：

```text
agent/wc_agent/retrievers.py
  MockKnowledgeRetriever
  ChromaRetriever
  ShujukuHttpRetriever
```

`ShujukuHttpRetriever.search()` 的职责只有三件：

1. 调用 `backend` 检索接口。
2. 把后端响应转换成 `Evidence`。
3. 过滤 `confidence < 0.7` 的结果。

Agent 后面的文化考据、设计、营销节点不需要知道数据来自 Chroma、SQLite 还是 HTTP。

## 6. 两台电脑协作注意事项

- 不提交 `.env`、API Key、数据库文件、上传文件和本地 Chroma 数据。
- 提交 `.env.example`，只放空 key 和默认字段名。
- Chroma 本地路径可以不同，但 `CHROMA_COLLECTION`、embedding 模型、向量维度、metadata 字段要一致。
- 每次开始开发前先 `git pull origin main`。
- 功能开发建议开分支，例如 `codex/agent-integration`、`feature/backend-search-api`。
