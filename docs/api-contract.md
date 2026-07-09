# API 契约草案

## GET /api/health

返回服务状态和当前 collection 名称。

## GET /api/documents

返回已登记资料列表。

## POST /api/ingest

```json
{
  "title": "资料标题",
  "content": "资料正文",
  "object_type": "internal_doc",
  "permission_level": "public"
}
```

## POST /api/search

```json
{
  "query": "客群画像指标",
  "user_type": "paid",
  "top_k": 5
}
```

## POST /api/ask

```json
{
  "question": "如何提升文旅项目二次消费？",
  "user_type": "paid",
  "top_k": 5
}
```

## GET /api/audit

返回最近的使用记录和审计日志。
