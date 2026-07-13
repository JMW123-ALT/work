# API Contract

所有接口由同一个 FastAPI 后端提供。正式前缀是 `/api/v1`，同时保留 `/api` 兼容前端旧调用。

## POST /api/v1/chat

文创 Agent 入口。

请求：

```json
{
  "query": "敦煌保温杯文创，偏国潮厚重风，输出小红书文案",
  "user_type": "visitor",
  "top_k": 5,
  "min_confidence": 0.7
}
```

响应核心字段：

```json
{
  "user_query": "...",
  "intent": "copywriting",
  "keywords": ["..."],
  "style": "国潮厚重风",
  "evidence": [],
  "cultural_review": "...",
  "design_plan": "...",
  "marketing_copy": "...",
  "warnings": [],
  "llm_modes": {
    "intent": "deepseek",
    "cultural_review": "deepseek",
    "design": "deepseek",
    "marketing": "deepseek"
  },
  "workflow": "langgraph",
  "status": "ok",
  "final_answer": "..."
}
```

`status` 可选值：

```text
ok
need_more_material
need_human_review
blocked
```

## POST /api/v1/chat/stream

文创 Agent SSE 流式入口。普通 `/api/v1/chat` 保持完整 JSON 返回，流式接口会按事件输出：

```text
event: start
event: delta
event: final
event: done
```

## POST /api/v1/search

语义检索，供调试、前端检索页和 Agent 内部复用。

## POST /api/v1/ask

普通 RAG 问答。

## POST /api/v1/ingest/text

JSON 文本入库。

## POST /api/v1/ingest/file

文件入库，支持 PDF、图片和 Office 文档。

## GET /api/v1/documents

查看当前入库资料。

## GET /api/v1/health

健康检查。
