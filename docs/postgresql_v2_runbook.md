# PostgreSQL + Chroma V2 操作说明

本文档用于本地联调资源库 v2 链路，给同事按步骤操作即可。

当前 v2 链路是独立测试链路，不会替换旧前端入库、旧 Chroma v1、旧 `/api/chat`。

## 1. 当前链路

```text
v2 入库
-> PostgreSQL documents / document_versions / document_files / chunks
-> v2 索引到 Chroma 集合 wenchuang_knowledge_v2
-> v2 检索
-> PostgreSQL 补全 chunk/document 元数据
-> 返回 Agent-ready evidence
```

旧链路仍然保留：

```text
旧前端上传页
-> /api/ingest 或 /api/v1/ingest
-> SQLite + Chroma v1
-> /api/chat
```

## 2. PostgreSQL 本地信息

当前本机 PostgreSQL 是免管理员安装。

```text
安装目录: D:\User\postgresql\app
数据目录: D:\User\postgresql\data
host: 127.0.0.1
port: 5432
database: wenchuang
user: wenchuang
password: wenchuang
```

项目 `.env` 需要包含：

```env
DATABASE_URL=postgresql+asyncpg://wenchuang:wenchuang@127.0.0.1:5432/wenchuang
DATABASE_URL_SYNC=postgresql+psycopg://wenchuang:wenchuang@127.0.0.1:5432/wenchuang
CHROMA_COLLECTION_V2=wenchuang_knowledge_v2
```

## 3. 启动 PostgreSQL

如果 PowerShell 可以运行脚本：

```powershell
D:\User\postgresql\start-postgresql.ps1
```

如果 PowerShell 禁止运行脚本，使用临时绕过方式：

```powershell
powershell -ExecutionPolicy Bypass -File D:\User\postgresql\start-postgresql.ps1
```

也可以不用脚本，手动启动：

```powershell
D:\User\postgresql\app\pgsql\bin\pg_ctl.exe -D D:\User\postgresql\data -l D:\User\postgresql\postgresql.log -o "-p 5432" start
```

查看状态：

```powershell
powershell -ExecutionPolicy Bypass -File D:\User\postgresql\status-postgresql.ps1
```

或：

```powershell
D:\User\postgresql\app\pgsql\bin\pg_ctl.exe -D D:\User\postgresql\data status
```

停止 PostgreSQL：

```powershell
powershell -ExecutionPolicy Bypass -File D:\User\postgresql\stop-postgresql.ps1
```

## 4. 初始化数据库结构

第一次使用或迁移更新后执行：

```powershell
cd D:\User\wrok1\work\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

成功后可检查：

```powershell
$env:PGPASSWORD="wenchuang"
D:\User\postgresql\app\pgsql\bin\psql.exe -h 127.0.0.1 -p 5432 -U wenchuang -d wenchuang -c "select version_num from alembic_version;"
```

期望结果：

```text
005_agent_runtime
```

## 5. 启动后端

```powershell
cd D:\User\wrok1\work\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

打开 Swagger：

```text
http://127.0.0.1:8000/api/docs
```

## 6. 健康检查

Swagger 调用：

```text
GET /api/v1/platform/database/health
```

期望：

```json
{
  "configured": true,
  "reachable": true,
  "status": "ready",
  "alembic_revision": "005_agent_runtime",
  "message": "Database is reachable."
}
```

常见状态：

- `not_configured`: `.env` 没有配置 `DATABASE_URL`
- `unreachable`: PostgreSQL 没启动或连接信息错误
- `no_migration`: 数据库能连，但还没执行 `alembic upgrade head`
- `ready`: 正常

## 7. v2 文本入库

Swagger 调用：

```text
POST /api/v1/platform/resources/text
```

测试请求：

```json
{
  "organization_id": "00000000-0000-4000-8000-00000000a001",
  "source_id": "xiuzhou-test-001",
  "title": "秀洲区郊野公园概念方案",
  "content": "这里放真实测试内容，例如项目定位、客群、文化资源、产品策划方向。",
  "modality": "text"
}
```

注意：

- `organization_id` 必须存在。
- 本地测试组织 ID 是 `00000000-0000-4000-8000-00000000a001`。
- 如果填 `org-1` 这类不存在的 ID，会返回 400。

成功响应示例：

```json
{
  "document_id": "...",
  "source_id": "xiuzhou-test-001",
  "title": "秀洲区郊野公园概念方案",
  "duplicate": false,
  "chunk_count": 1,
  "version_id": "...",
  "file_id": null,
  "vector_status": "pending"
}
```

## 8. v2 文件入库

Swagger 调用：

```text
POST /api/v1/platform/resources/file
```

Form 参数：

```text
organization_id = 00000000-0000-4000-8000-00000000a001
title = 文件标题
file = 选择 PDF / txt / docx / pptx / xlsx / 图片
```

成功后会写入：

- `documents`
- `document_versions`
- `document_files`
- `chunks`

文件重复上传时会按 `file_sha256` 去重。

## 9. v2 向量索引

入库后，chunk 的 `vector_status` 是 `pending`，需要手动索引到 Chroma v2。

Swagger 调用：

```text
POST /api/v1/platform/vector-index/run
```

请求：

```json
{
  "limit": 100
}
```

成功响应：

```json
{
  "collection": "wenchuang_knowledge_v2",
  "indexed": 1,
  "failed": 0,
  "errors": []
}
```

说明：

- 文本 chunk 走 `embed_text`
- 有 `asset_path` 的 PDF 页或图片 chunk 走 `embed_multimodal`
- Chroma v2 的 ID 使用 PostgreSQL `chunks.id`
- 原始 chunk id 保存在 metadata 的 `legacy_chunk_id`

## 10. v2 检索

Swagger 调用：

```text
POST /api/v1/platform/search
```

请求：

```json
{
  "query": "秀洲区郊野公园 文创 产品策划",
  "user_type": "visitor",
  "top_k": 5,
  "min_confidence": 0
}
```

成功响应会返回：

- `items[].text`
- `items[].source`
- `items[].confidence`
- `items[].metadata.chunk_id`
- `items[].metadata.legacy_chunk_id`
- `items[].metadata.page_number`
- `items[].metadata.asset_path`
- `items[].metadata.embedding_modality`

## 11. 推荐测试顺序

每次本地联调按这个顺序：

```text
1. 启动 PostgreSQL
2. 启动后端
3. GET  /api/v1/platform/database/health
4. POST /api/v1/platform/resources/text 或 /platform/resources/file
5. POST /api/v1/platform/vector-index/run
6. POST /api/v1/platform/search
```

## 12. 常见问题

### PowerShell 禁止运行 ps1

报错：

```text
因为在此系统上禁止运行脚本
```

使用：

```powershell
powershell -ExecutionPolicy Bypass -File D:\User\postgresql\start-postgresql.ps1
```

### organization_id 不存在

报错：

```text
organization_id does not exist
```

本地测试使用：

```text
00000000-0000-4000-8000-00000000a001
```

### Chroma v2 维度不一致

报错类似：

```text
Chroma v2 collection dimension mismatch
```

原因通常是之前用本地 embedding 建过 `wenchuang_knowledge_v2`，后来切到真实 qwen embedding，向量维度不同。

处理方式：

1. 删除 `wenchuang_knowledge_v2` 集合。
2. 把 PostgreSQL 中已索引 chunk 重置为 `pending`。
3. 重新执行 `/api/v1/platform/vector-index/run`。

### v2 search 没结果

检查：

1. 是否已经入库成功。
2. 是否执行过 `/api/v1/platform/vector-index/run`。
3. `min_confidence` 是否太高，测试时可以先设为 `0`。
4. query 是否和入库内容有明显相关词。

## 13. 当前边界

当前 v2 链路已经可以独立跑通：

```text
v2 入库 -> v2 索引 -> v2 检索
```

但还没有把 Agent 切换到 v2。

也就是说：

- `/api/v1/platform/search` 是 v2 检索
- `/api/v1/search` 还是旧 v1 检索
- `/api/chat` 还是旧 v1 RAG

后续确认 v2 资料质量、PDF 切分、多模态索引稳定后，再做 Agent 可选切换到 v2 RAG。
