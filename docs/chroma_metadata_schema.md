# Chroma 1.4.4 知识库字段对接规范

更新时间：2026-07-09

本文件根据同事提供的 Chroma 字段截图整理，用于指导文创 Agent 接入知识库。

## 1. Chroma 原生字段

同事知识库使用 Chroma 1.4.4，collection 中每条 chunk 的基础字段如下：

| Chroma 字段 | 约定 | 说明 |
|---|---|---|
| `id` | 使用 `chunk_id` | Chroma 每条记录的唯一 ID |
| `document` | chunk 正文内容 | Agent 最终放进 `Evidence.text` |
| `embedding` | `list[float]` | 向量，由数据库侧生成和维护 |
| `metadata` | 业务字段集合 | 见下一节 |

## 2. Metadata 字段

同事给定的 metadata 字段：

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

字段含义建议：

| 字段 | 类型建议 | 含义 |
|---|---|---|
| `chunk_id` | string | chunk 唯一 ID，同时作为 Chroma `id` |
| `source_id` | string | 原始资料 ID，一个 source 可切多个 chunk |
| `chunk_index` | int | chunk 在资料中的序号 |
| `section_path` | string | 章节路径或资料层级 |
| `modality` | string | text / image / pdf / office 等 |
| `parser` | string | 解析器名称 |
| `title` | string | 资料标题 |
| `object_type` | string | 资料类型，如 culture_doc、case_summary、policy_doc |
| `permission_level` | string | public / free / paid / internal / restricted |
| `access_channel` | string | web、upload、api 等来源渠道 |
| `original_ref_uri` | string | 原始资料 URI 或上传引用 |
| `file_name` | string | 原始文件名 |
| `mime_type` | string | 文件 MIME 类型 |
| `file_size` | int | 文件大小 |
| `chunk_count` | int | 同一 source 的 chunk 总数 |
| `extraction_status` | string | parsed / placeholder / failed 等 |
| `runtime` | int/bool | 是否运行时上传资料 |
| `created_at` | string | 创建时间 |
| `updated_at` | string | 更新时间 |

## 3. 映射到文创 Agent Evidence

文创 Agent 内部统一使用 `Evidence`：

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

当前映射规则：

| Chroma 字段 | Evidence 字段 | 当前代码规则 |
|---|---|---|
| `document` | `text` | 直接使用 chunk 正文 |
| `metadata.source_id` | `source` | 转成 `shujuku:<source_id>` |
| `metadata.object_type` | `category` | 作为资料类别 |
| `metadata.title` | `culture_theme` | 优先使用标题；没有标题再用 `section_path` |
| `distance` | `confidence` | 通过 `1 - distance` 粗略转换 |
| `metadata.permission_level` | `copyright_status` | public -> public_domain；free/paid/internal -> authorized；其他 unknown |
| `metadata.permission_level` | `risk_level` | internal/restricted -> medium；其他 low |

对应代码：

```text
wc_agent/retrievers.py::chroma_result_to_evidence
```

## 4. 当前还缺的文创专用字段

同事当前 schema 能跑通检索，但对文创 Agent 来说还缺几个更精确的业务字段：

```text
culture_theme
category
copyright_status
risk_level
source
```

建议后续在 metadata 中直接增加：

| 建议新增字段 | 原因 |
|---|---|
| `culture_theme` | 比 title 更适合表示“敦煌藻井 / 唐代纹样 / 非遗授权”等文化主题 |
| `category` | 区分纹样、配色、产品、营销、合规、策展 |
| `copyright_status` | 直接服务商用版权判断 |
| `risk_level` | 直接服务后置风控 |
| `source` | 显示给用户看的来源名或引用 |

如果暂时不新增，也可以使用当前适配器兜底映射。

## 5. 接入结论

现在文创 Agent 可以按这个 Chroma schema 接入：

```text
Chroma collection
-> ChromaRetriever.search()
-> chroma_result_to_evidence()
-> Evidence
-> LangGraph 文化考据/设计/营销节点
```

今天要做的重点不是改 Chroma 入库，而是确保双方确认：

1. `id` 必须等于 `chunk_id`。
2. `document` 必须是 chunk 正文。
3. `metadata` 至少包含截图里的 19 个字段。
4. 后续最好补充文创专用字段，减少 Agent 侧猜测。

## 6. 当前模型 API 配置

同事使用的模型已经在本项目中预留配置：

```text
EMBEDDING_MODEL=qwen3-vl-embedding
RERANK_MODEL=qwen3-rerank
```

本地真实 key 写在 `.env` 中，示例配置写在 `.env.example` 中。

注意：`qwen3-vl-embedding` 不走 OpenAI-compatible `/embeddings`，而是走 DashScope 原生多模态接口：

```text
EMBEDDING_DASHSCOPE_URL=<...>/api/v1
POST /services/embeddings/multimodal-embedding/multimodal-embedding
```

`qwen3-rerank` 走 DashScope rerank 接口：

```text
RERANK_BASE_URL=<...>/api/v1
POST /services/rerank/text-rerank/text-rerank
```

当前策略：

| 能力 | 当前状态 | 说明 |
|---|---|---|
| query embedding | 已接入可选客户端 | `ChromaRetriever` 会在有 key 时用 `query_embeddings` 查询 |
| rerank | 已接入可选客户端 | 默认 `RERANK_ENABLED=false`，避免没有真实 Chroma 时产生额外调用 |
| 主回答模型 | 已接 DeepSeek | 负责组织最终文创方案 |

正式联调同事 Chroma 后，如果初召回结果正常，再把：

```text
RERANK_ENABLED=true
```

打开，使用 `qwen3-rerank` 对 Top-N 结果精排。
