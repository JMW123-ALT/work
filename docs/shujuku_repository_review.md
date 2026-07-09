# 同事数据库仓库检查结果

检查日期：2026-07-09

仓库地址：https://github.com/JMW123-ALT/shujuku

本地解压位置：

```text
D:\User\shujuku
```

## 1. 结论

这个仓库目前不是 Chroma 实库，而是一个完整的文旅向量数据库 Web 系统雏形：

```text
backend/   FastAPI 后端
frontend/  前端页面
docs/      架构和 API 契约
```

当前后端使用：

```text
SQLite 持久化文档、metadata、chunk、占位向量
```

Chroma 配置已经预留，但 README 明确写着当前 MVP 阶段仍使用 SQLite：

```text
backend/data/vector_store.sqlite3
```

所以最初检查时不建议把它当成 Chroma collection 直接接入。现在同事已经补充 Chroma 1.4.4 字段规范，因此正式知识库可用后，可以优先用当前文创 Agent 的 `ChromaRetriever` 接入。

正式 Chroma 字段规范见：

```text
D:\User\work\docs\chroma_metadata_schema.md
```

## 2. 关键文件

| 文件 | 作用 |
|---|---|
| `D:\User\shujuku\backend\app\services\vector_store.py` | SQLite 向量库核心，实现 `search()` |
| `D:\User\shujuku\backend\app\services\rag_service.py` | RAG 编排：检索 -> rerank -> LLM |
| `D:\User\shujuku\backend\app\services\embedding_client.py` | embedding 边界，当前可本地占位，后续可接 DashScope |
| `D:\User\shujuku\backend\app\services\rerank_client.py` | rerank 边界，当前 passthrough，后续可接 DashScope |
| `D:\User\shujuku\backend\app\core\config.py` | 配置项，包括 DeepSeek、Embedding、Rerank、Chroma 预留 |
| `D:\User\shujuku\backend\data\seed_documents.json` | 默认演示资料 |

## 3. 同事项目的检索接口

核心接口在：

```python
vector_store.search(query: str, user_type: str = "visitor", top_k: int = 5) -> dict
```

返回结构：

```python
{
    "items": [...],
    "blockedCount": 0
}
```

每个 item 主要字段：

```text
source_id
title
content
object_type
permission_level
access_channel
original_ref_uri
section_path
modality
score
snippet
chunk_id
chunk_index
```

## 4. 与文创 Agent Evidence 的字段映射

当前文创 Agent 需要：

```python
Evidence(
    text="史料正文",
    source="来源",
    category="类别",
    culture_theme="文化主题",
    confidence=0.82,
    copyright_status="public_domain/authorized/unknown",
    risk_level="low/medium/high",
)
```

建议映射：

| 同事数据库字段 | 文创 Agent 字段 | 说明 |
|---|---|---|
| `content` / `snippet` | `text` | 优先使用 chunk 内容 |
| `source_id` | `source` | 可拼成 `shujuku:<source_id>` |
| `object_type` | `category` | 比如 public_doc、case_summary |
| `title` / `section_path` | `culture_theme` | 当前没有专门文化主题字段，先用标题 |
| `score` | `confidence` | SQLite 检索余弦分数 |
| `permission_level` | `copyright_status` | public 可视为 public_domain，其他可视为 authorized/unknown |
| `object_type` / `permission_level` | `risk_level` | restricted/internal 可标 medium，其他 low |

如果使用同事 Chroma 1.4.4 schema，当前代码中的映射函数是：

```text
wc_agent/retrievers.py::chroma_result_to_evidence
```

核心规则：

| Chroma 字段 | Evidence 字段 |
|---|---|
| `document` | `text` |
| `metadata.source_id` | `source` |
| `metadata.object_type` | `category` |
| `metadata.title` | `culture_theme` |
| `metadata.permission_level` | `copyright_status` / `risk_level` |

## 5. 当前风险

1. 默认种子数据不是文创史料，而是文旅项目资料。
2. 目前没有 `culture_theme`、`copyright_status`、`risk_level` 这些文创 Agent 专用字段。
3. 当前仓库 Chroma 起初只是预留；现在已有 Chroma 1.4.4 字段规范，但还需要确认实际 collection 路径/名称和数据是否已经生成。
4. 本地环境缺少同事项目依赖：`pydantic-settings`、`fastapi` 等，需要单独安装后才能运行。
5. 同事项目默认端口也是 `8000`，会和当前文创 Agent API 冲突，建议它运行在 `8001`。

## 6. 推荐操作顺序

### 第一步：先安装并跑通同事后端

```powershell
cd D:\User\shujuku\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

打开：

```text
http://127.0.0.1:8001/docs
```

### 第二步：测试同事检索接口

请求：

```json
{
  "query": "文旅项目 二次消费",
  "user_type": "paid",
  "top_k": 5
}
```

预期：

```text
能返回 sources/items，且包含 score、content、source_id 等字段。
```

### 第三步：确认 Chroma collection

让同事提供：

```text
CHROMA_PATH
CHROMA_COLLECTION
embedding_model
distance/metric 类型
```

并确认 metadata 至少包含：

```text
chunk_id
source_id
chunk_index
section_path
modality
parser
title
object_type
permission_level
access_channel
original_ref_uri
file_name
mime_type
file_size
chunk_count
extraction_status
runtime
created_at
updated_at
```

### 第四步：建议让同事补齐文创字段

建议让同事后续入库时增加 metadata：

```text
culture_theme
category
copyright_status
risk_level
source
```

这样文创 Agent 可以少写很多猜测逻辑。

### 第五步：选择接入方式

如果同事项目作为独立服务运行，推荐写 HTTP 适配器：

```text
Wenchuang Agent -> http://127.0.0.1:8001/api/v1/search -> Evidence
```

如果希望直接读同事 SQLite，则写 SQLite 适配器：

```text
Wenchuang Agent -> D:\User\shujuku\backend\data\vector_store.sqlite3 -> Evidence
```

如果正式 Chroma collection 已经可用，优先使用当前 `ChromaRetriever`。如果同事只跑后端服务，则使用 HTTP 适配器。不要直接耦合 SQLite 表结构，除非临时演示必须这样做。

## 7. 今日建议

今天先不要切换正式数据库。今天最该完成：

1. 跑通同事后端 `8001`。
2. 用 `/api/v1/search` 验证检索结果字段。
3. 和同事确认 Chroma path、collection、metric、metadata 字段。
4. 用 `ChromaRetriever` 做一次真实检索验证。
