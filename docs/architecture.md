# 架构说明

## 当前雏形

```text
Web 前端
  -> /api/ingest 资料登记
  -> /api/search 权限过滤检索
  -> /api/ask RAG 问答
  -> /api/audit 审计记录

后端服务
  -> permissions.py 权限上下文
  -> vector_store.py SQLite 持久化向量库
  -> embedding_client.py 本地 embedding 占位
  -> llm_client.py DeepSeek 占位
  -> audit.py 使用记录
```

## 向量库状态

现在已经不再只使用内存检索。资料、metadata 和本地占位向量会写入：

```text
backend/data/vector_store.sqlite3
```

`vector_store.py` 保持了 `list_documents`、`add_document`、`search` 等接口，后续切换 Chroma 时尽量不影响 Web 和 RAG 服务。

## 下一步替换点

- `embedding_client.py`：接入真实 embedding API。
- `vector_store.py`：如果确认 Chroma 包或服务可用，可替换为 Chroma collection `tourism_knowledge_vectors`。
- `llm_client.py`：接入 DeepSeek，使用检索片段生成结构化回答。
- `permissions.py`：从真实用户系统或 MySQL 获取权限上下文。

## 权限原则

无权限命中时，只返回“存在更高权限资料”的提示，不返回标题、客户名、项目名、原始数值或附件路径。
