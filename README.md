# Wenchuang Agent

单后端、单端口、单数据目录的文旅文创 Agent 项目。后端负责资料入库、Chroma 检索、RAG 问答和文创 Agent 生成；前端是静态页面，由同一个 FastAPI 服务挂载。

## 当前能力

- 资料入库：支持文本、PDF、Office 等文件上传和解析。
- 本地知识库：SQLite 存 metadata，Chroma 存向量索引。
- RAG 检索：支持 `top_k`、`min_confidence`、权限过滤和 rerank 占位/扩展。
- 文创 Agent：LangGraph 编排，流程包括需求解析、检索、风控、文化考据、方案设计和营销文案。
- LLM：通过 OpenAI SDK 兼容调用 DeepSeek。
- 流式接口：提供 SSE 形式的 Agent 输出接口。
- 单端口运行：默认 `http://127.0.0.1:8000`。

## 项目结构

```text
frontend/
  index.html              静态前端页面
  app.js                  前端接口调用
  styles.css              页面样式

backend/
  app/main.py             FastAPI 应用入口
  app/api/v1/             API 路由
  app/services/agent.py   文创 Agent / LangGraph 流程
  app/services/llm_client.py
                          DeepSeek / OpenAI SDK 封装
  app/services/vector_store.py
                          SQLite + Chroma 知识库
  app/services/rag_service.py
                          检索、rerank、问答编排
  scripts/smoke_agent.py  最小链路 smoke 测试
  tests/                  后端测试

docs/                     架构、接口和 Agent 流程说明
run.ps1                   Windows 一键启动脚本
```

## 环境配置

复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`，至少配置：

```text
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=https://ws-n81tu3iqo4jsalm2.cn-beijing.maas.aliyuncs.com/api/v1
EMBEDDING_MODEL=qwen3-vl-embedding

DATA_DIR=backend/data
UPLOAD_DIR=backend/data/uploads
CHROMA_PATH=backend/data/chroma
CHROMA_COLLECTION=wenchuang_knowledge
MIN_RETRIEVAL_CONFIDENCE=0.7
```

注意：`.env` 里有真实 API Key，不能提交到 GitHub。仓库只提交 `.env.example`。

## 启动

在项目根目录运行：

```powershell
.\run.ps1
```

脚本会自动：

- 创建/复用 `backend/.venv`
- 安装 `backend/requirements.txt`
- 读取 `.env`
- 启动 FastAPI 后端

启动后访问：

```text
前端页面: http://127.0.0.1:8000/
Swagger:  http://127.0.0.1:8000/api/docs
Agent:    http://127.0.0.1:8000/api/chat
```

日志位置：

```text
.runtime/backend.out.log
.runtime/backend.err.log
```

## 主要接口

正式接口前缀是 `/api/v1`，同时保留 `/api` 兼容旧前端调用。

| 接口 | 用途 |
|---|---|
| `GET /api/health` | 健康检查 |
| `POST /api/chat` | 文创 Agent 对话 |
| `POST /api/v1/chat/stream` | 文创 Agent SSE 流式输出 |
| `POST /api/search` | 语义检索 |
| `POST /api/ask` | 普通 RAG 问答 |
| `POST /api/v1/ingest/text` | 文本入库 |
| `POST /api/v1/ingest/file` | 文件入库 |
| `GET /api/documents` | 查看入库资料 |

Agent 请求示例：

```json
{
  "query": "根据秀洲区郊野公园概念方案给我出一个方案",
  "user_type": "visitor",
  "top_k": 5,
  "min_confidence": 0.7
}
```

Agent 响应里可重点看：

```json
{
  "status": "ok",
  "workflow": "langgraph",
  "llm_modes": {
    "intent": "deepseek",
    "cultural_review": "deepseek",
    "design": "deepseek",
    "marketing": "deepseek"
  },
  "evidence": [],
  "final_answer": "..."
}
```

## 测试

后端测试使用项目根目录的 `.venv`：

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m ruff check app tests scripts
```

依赖检查：

```powershell
cd ..
.\backend\.venv\Scripts\python.exe -m pip check
```

## Smoke 测试

后端启动后，运行最小链路 smoke：

```powershell
cd backend
..\.venv\Scripts\python.exe scripts\smoke_agent.py --base-url http://127.0.0.1:8000
```

它会检查：

- `GET /api/health`
- `POST /api/v1/search`
- `POST /api/chat`
- `POST /api/v1/chat/stream`

输出中 `chat` 的 `llm_modes` 应显示 DeepSeek 节点是否真实调用：

```json
{
  "intent": "deepseek",
  "cultural_review": "deepseek",
  "design": "deepseek",
  "marketing": "deepseek"
}
```

## 数据目录

运行时数据统一放在：

```text
backend/data/vector_store.sqlite3
backend/data/chroma/
backend/data/uploads/
```

这些目录通常不提交到 GitHub。团队协作时，如果同事更新入库数据，需要同步 `backend/data` 下对应文件或重新入库。

## Git 协作

当前推荐流程：

```powershell
git switch main
git pull
git switch -c 你的分支名

# 修改代码后
git add .
git commit -m "feat: your change"
git push -u origin 你的分支名
```

然后在 GitHub 上从你的分支创建 Pull Request，合并到 `main`。

## 注意事项

- 不要提交 `.env`、`.venv`、`.runtime`、`backend/data`。
- 如果 8000 端口被旧进程占用，先关闭旧后端再运行 `.\run.ps1`。
- `/api/v1/chat/stream` 是 SSE 接口，前端需要按事件流读取。
- 如果检索分数低于 `min_confidence` 但仍有候选资料，Agent 会生成可讨论草案并返回 `need_human_review`。
