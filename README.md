# 文旅知识库 + 文创 Agent 联调项目

这个仓库现在合并两部分能力：

- `backend/`：同事维护的文旅知识库后端，负责资料入库、权限过滤、向量检索、审计记录等能力。
- `frontend/`：知识库演示前端。
- `agent/`：文创智能体，负责需求理解、RAG 检索、文化考据、创意设计、营销文案与流式输出。
- `docs/`：双方共享的架构、Chroma 字段、Agent 流程和模型选型文档。

当前整合方式是一个项目、两个服务、一个数据中心：`backend/` 负责唯一的数据入库和检索，`agent/` 通过 `POST /api/v1/search` 使用 `backend/data` 中已有的 SQLite/Chroma 数据。

## 推荐目录结构

```text
shujuku/
  backend/        # 知识库后端
  frontend/       # 知识库前端
  agent/          # 文创 Agent 子工程
  docs/           # 共享文档
  .env.example    # 联调环境变量模板，不放真实 key
  .gitignore
  README.md
```

## 环境配置

复制根目录模板：

```powershell
cd D:\User\work\shujuku
Copy-Item .env.example .env
```

然后在 `.env` 里填真实配置。注意 `.env` 已经被 `.gitignore` 忽略，不要把真实 API Key 提交到 GitHub。

关键配置：

```text
LLM_API_KEY=你的 DeepSeek Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash

EMBEDDING_API_KEY=你的 qwen3-vl-embedding Key
EMBEDDING_PROVIDER=dashscope
EMBEDDING_BASE_URL=https://ws-n81tu3iqo4jsalm2.cn-beijing.maas.aliyuncs.com/api/v1
EMBEDDING_MODEL=qwen3-vl-embedding

RERANK_API_KEY=你的 qwen3-rerank Key
RERANK_MODEL=qwen3-rerank
RERANK_ENABLED=false

CHROMA_PATH=backend/data/chroma
CHROMA_COLLECTION=tourism_knowledge_vectors
MIN_RETRIEVAL_CONFIDENCE=0.7

RETRIEVER_PROVIDER=shujuku
SHUJUKU_SEARCH_URL=http://127.0.0.1:8001/api/v1/search
```

如果 `backend/data/chroma` 之前是本地占位向量，配置好 qwen3 key 后需要重建一次 Chroma：

```powershell
cd D:\User\work\shujuku
.\backend\.venv\Scripts\python.exe backend\scripts\rebuild_chroma.py
```

重建只会用 `backend/data/vector_store.sqlite3` 里的 documents 重新生成 Chroma 向量索引，不会删除 SQLite 文档数据。

## 一键启动完整项目

```powershell
cd D:\User\work\shujuku
.\run.ps1
```

启动后：

```text
Backend API: http://127.0.0.1:8001/api/docs
Agent API:   http://127.0.0.1:8000/docs
```

`run.ps1` 会分别使用：

```text
backend/.venv
agent/.venv
```

不要让两个服务共用同一个虚拟环境，后端和 Agent 的 LangChain/LangGraph 依赖版本不同。

## 单独启动知识库后端

```powershell
cd D:\User\work\shujuku\backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

后端文档：

```text
http://127.0.0.1:8001/api/docs
```

## 单独启动文创 Agent

Agent 单独启动时，如果要用 `backend/data` 中的真实数据，需要设置 `RETRIEVER_PROVIDER=shujuku`。

```powershell
cd D:\User\work\shujuku\agent
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:RETRIEVER_PROVIDER="shujuku"
$env:SHUJUKU_SEARCH_URL="http://127.0.0.1:8001/api/v1/search"
.\.venv\Scripts\python.exe -m uvicorn wc_agent.api:app --host 127.0.0.1 --port 8000
```

Agent 文档：

```text
http://127.0.0.1:8000/docs
```

命令行测试：

```powershell
cd D:\User\work\shujuku\agent
.\.venv\Scripts\python.exe wenchuang_agent.py "敦煌保温杯文创，偏国潮厚重风，输出小红书文案"
```

## 项目边界

当前分工：

- 知识库同事维护 `backend/`、`frontend/`、入库逻辑、Chroma/SQLite 数据和权限。
- 你维护 `agent/` 的智能体流程、LLM 调用、RAG 编排和输出格式。
- 双方共同维护 `POST /api/v1/search` 的返回字段契约。

Agent 不直接读取 `backend/data`，只调用 `backend` 的检索接口。这样既保留项目完整性，又不会让两边代码互相耦合。

## 共享文档

- `docs/project_architecture.md`：文创 Agent 工程架构。
- `docs/agent_flow.md`：Agent RAG 流程。
- `docs/chroma_metadata_schema.md`：Chroma 元数据字段规范。
- `docs/integration_plan.md`：Agent 与知识库后端联调方式。
- `docs/model_selection.md`：向量模型、召回模型、回答模型选型。
- `docs/demo_cases.md`：演示案例。

## Git 协作建议

```powershell
git pull origin main
git checkout -b codex/agent-integration
git status
```

确认运行没问题后再提交：

```powershell
git add README.md .env.example .gitignore agent docs
git commit -m "Add wenchuang agent integration structure"
git push origin codex/agent-integration
```
