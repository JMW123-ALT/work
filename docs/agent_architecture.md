# Agent Architecture

This document records the first-stage Agent platform structure. It is a design
and runtime framework document only. The current executable business Agent is
still `legacy_wenchuang_agent_v1` exposed through `/api/chat`; future business
Agents listed here are not implemented in this stage.

## Stage Boundary

Current stage keeps the working v1 flow:

```text
user request
-> existing Wenchuang Agent v1
-> resource retrieval
-> qwen3-vl-rerank
-> DeepSeek answer generation
-> response
```

The stage adds platform structure for:

- resource taxonomy and governance dimensions
- workflow run records
- agent run records and parent-child relationships
- evidence records that can trace back to documents, chunks, and page numbers
- artifacts and artifact versions
- reviews and future human interrupt points
- prompt templates, platform profiles, and intelligence items

It does not implement new business Agent nodes or new business prompts.

## Resource Library Foundation

PostgreSQL will become the future source of truth for structured metadata:

- organizations, users, projects, project requirements
- documents, document versions, document files
- chunks and chunk metadata
- categories and tags
- permissions, confidentiality, copyright, risk, lifecycle
- ingestion tasks and vector indexing tasks
- workflow and artifact runtime records

Chroma remains responsible only for vector storage and vector recall. The v2
collection name is `wenchuang_knowledge_v2`. Chroma IDs in the PostgreSQL-backed
system must map to PostgreSQL chunk IDs. The current v1 SQLite and Chroma data
must remain untouched until users explicitly rebuild or re-upload data into the
v2 system.

The resource category seed tree is:

- `internal` 公司内部资料
- `internal.project.completed` 已完成项目资料
- `internal.project.in_progress` 正在进行项目资料
- `internal.operation.feedback` 运营端反馈实施数据
- `external` 外部收集资料
- `external.project.case` 其他项目资料
- `external.report.comprehensive` 文件信息综合报告
- `external.report.professional_analysis` 专项专业分析报告
- `confidential` 特殊平台保密资料
- `confidential.authorized.government` 政府授权项目数据
- `confidential.authorized.group` 集团公司授权项目数据
- `confidential.report.project_analysis` 项目分析专项报告
- `confidential.report.multi_role_review` 多角色复核报告
- `other` 其他资料
- `other.policy.current` 当前版本政策文件
- `other.cross_industry.creativity` 跨行业前瞻创意
- `other.cross_industry.design` 跨行业设计案例
- `other.cross_industry.story` 跨行业故事案例

Governance dimensions stay independent:

- Category: business category tree
- Permission: organization, project, user, or role access scope
- Confidentiality: public, internal, restricted, confidential
- Copyright: unknown, owned, licensed, public_domain, restricted, prohibited
- Risk: low, medium, high, blocked
- Lifecycle: draft, active, archived, expired, deleted

## Agent Blueprint

### Current Executable Agent

`legacy_wenchuang_agent_v1`

- Preserves `/api/chat`
- Preserves DeepSeek real model calls
- Preserves resource retrieval, qwen3-vl-embedding, qwen3-vl-rerank
- Outputs `final_answer` and `evidence`

### Future Top-Level Agents

`online_collection_agent`

- Output: `background_report`
- Future responsibility: collect project materials, policy, news, cases, traffic
  and consumption data; then ingest, chunk, embed, rerank, and produce a
  background report with evidence.

`planning_outline_agent`

- Output: `outline_candidates`, `selected_outline`
- Future responsibility: role positioning, professional positioning, red/blue
  thinking, and 2 to 3 outline directions.
- User selection must use LangGraph interrupt instead of a standalone Agent.

`full_proposal_agent`

- Output: `full_proposal`
- Future responsibility: write the full plan and verify it through expert,
  investor, government, and operation perspectives.

`proposal_orchestrator_agent`

- Output: `presentation_plan`, `pptx`, `brochure`, `chart_spec`,
  `generated_image`
- Future responsibility: coordinate PPT, chart, image, and file output tools.
  These tools are not top-level Agents.

`cultural_ip_orchestrator_agent`

- Output: `ip_core_asset`, `project_cultural_product`
- Future responsibility: coordinate IP generation and single-project cultural
  product generation. It must not be split into more top-level Agents.

`external_output_orchestrator_agent`

- Output: `operation_intelligence`, `xiaohongshu_content`, `douyin_script`,
  `wechat_article`, `video_account_script`
- Future responsibility: coordinate operation intelligence and platform output
  content. Platform-specific workers remain sub-Agents.

### Future Sub-Agents

`core_ip_sub_agent`

- Parent: `cultural_ip_orchestrator_agent`
- Output: `ip_core_asset`

`project_cultural_product_sub_agent`

- Parent: `cultural_ip_orchestrator_agent`
- Output: `project_cultural_product`

`operation_intelligence_sub_agent`

- Parent: `external_output_orchestrator_agent`
- Output: `operation_intelligence`

`xiaohongshu_sub_agent`

- Parent: `external_output_orchestrator_agent`
- Output: `xiaohongshu_content`

`douyin_sub_agent`

- Parent: `external_output_orchestrator_agent`
- Output: `douyin_script`

`wechat_video_sub_agent`

- Parent: `external_output_orchestrator_agent`
- Output: `wechat_article`, `video_account_script`

## LangGraph Main Graph Design

The main graph is a coordinator, not an independent Agent:

```text
START
-> load_project
-> parse_request
-> route_task
```

Planning chain:

```text
online_collection_agent
-> background_report
-> planning_outline_agent
-> outline_candidates
-> interrupt: wait for user selection
-> selected_outline
-> full_proposal_agent
-> full_proposal
-> proposal_orchestrator_agent
-> human review
-> END
```

Cultural IP branch:

```text
online_collection_agent
-> cultural_ip_orchestrator_agent
-> core_ip_sub_agent or project_cultural_product_sub_agent
-> human review
-> END
```

External output branch:

```text
operation_intelligence_sub_agent
-> external_output_orchestrator_agent
-> xiaohongshu_sub_agent / douyin_sub_agent / wechat_video_sub_agent
-> human review
-> END
```

## Runtime Records

`workflow_runs` records the whole task.

Required fields later include:

- id
- project_id
- user_id
- task_type
- status
- input_payload
- created_at
- updated_at

`agent_runs` records each Agent execution.

Required fields later include:

- id
- workflow_run_id
- agent_code
- parent_agent_run_id
- status
- input_payload
- output_payload
- error_message
- created_at
- updated_at

`agent_run_steps` records node-level execution.

`agent_evidence` records the evidence chain:

- workflow_run_id
- agent_run_id
- artifact_id
- document_id
- chunk_id
- source_id
- page_number
- quote
- score
- metadata

`artifacts` records outputs such as background reports, outlines, full
proposals, IP assets, platform scripts, PPT plans, and generated images.

`artifact_versions` records revisions. `artifact_dependencies` records which
artifact was derived from which upstream artifact.

`reviews` records human review status. Future LangGraph interrupts should use
review records to resume workflows.

## Failure, Retry, And Recovery

- Ingestion failure must preserve the document or task state instead of
  silently dropping data.
- Vector indexing failure must keep PostgreSQL chunks as the source of truth and
  allow reindexing into `wenchuang_knowledge_v2`.
- Agent failures must be recorded in `agent_runs.error_message`.
- A failed sub-Agent must not delete upstream artifacts.
- Human review states should use `waiting_user`.
- Retried tasks must not create duplicate chunks or duplicate Chroma vectors.

## PostgreSQL Readiness

The PostgreSQL layer is a foundation layer only. The current v1 upload,
SQLite, Chroma, RAG, and `/api/chat` flow remains unchanged until the team
explicitly migrates ingestion to PostgreSQL plus Chroma v2.

When Docker is available, start the infrastructure from the repository root:

```powershell
docker compose up -d postgres redis
```

Then apply migrations from the backend directory:

```powershell
cd D:\User\wrok1\work\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Use the readiness endpoint to check whether the backend can reach PostgreSQL
and read the Alembic revision:

```text
GET /api/v1/platform/database/health
```

Status meanings:

- `not_configured`: `DATABASE_URL` is empty; old v1 flow can still run.
- `unreachable`: `DATABASE_URL` is set but PostgreSQL is not reachable.
- `no_migration`: PostgreSQL is reachable but `alembic upgrade head` has not
  been applied.
- `ready`: PostgreSQL is reachable and the Alembic revision can be read.

## PostgreSQL V2 Ingestion Entry Points

The current upload page and old endpoints still use the v1 SQLite plus Chroma
flow. The first PostgreSQL ingestion entry points are independent test paths:

```text
POST /api/v1/platform/resources/text
POST /api/v1/platform/resources/file
```

These endpoints write PostgreSQL metadata only:

- `documents`
- `document_versions`
- `document_files` for file uploads
- `chunks`

They do not write Chroma v2 yet. New chunks are marked `vector_status=pending`
so the next step can index PostgreSQL chunks into `wenchuang_knowledge_v2`.
When `DATABASE_URL` is not configured, these endpoints return 503 and the old
v1 upload flow remains usable.

## Chroma V2 Indexing

PostgreSQL chunks can be indexed into the v2 Chroma collection manually:

```text
POST /api/v1/platform/vector-index/run
```

Request body:

```json
{"limit": 100}
```

The indexer reads chunks where `vector_status` is `pending` or `failed`,
generates embeddings, and upserts them into `CHROMA_COLLECTION_V2`
(`wenchuang_knowledge_v2` by default). The Chroma ID is the PostgreSQL
`chunks.id`, while the old source chunk id is stored as metadata
`legacy_chunk_id`.

Status flow:

```text
pending -> indexed
pending -> failed
failed  -> indexed
```

For image/PDF-page chunks with `asset_path`, the indexer calls multimodal
embedding. Text-only chunks call text embedding. This v2 indexing path is still
independent from the current v1 RAG search; switching `/api/chat` to v2 recall
is a later step.

Celery task entry point:

```text
platform.vector_index_pending
```

## Chroma V2 Retrieval

The independent v2 retrieval endpoint is:

```text
POST /api/v1/platform/search
```

It uses the same request and response shape as the current v1 search endpoint,
but reads from the v2 path:

```text
query
-> embedding
-> CHROMA_COLLECTION_V2
-> PostgreSQL chunks/documents hydration
-> rerank
-> Agent-ready evidence items
```

The endpoint returns evidence fields compatible with the existing Agent-facing
search response. Metadata includes PostgreSQL `chunk_id`, `legacy_chunk_id`,
page number, asset path, asset MIME type, and embedding modality when
available.

This is still not wired into `/api/chat`. The current Agent keeps using the v1
RAG path until v2 ingestion, indexing, and retrieval are validated with real
PostgreSQL and Chroma data.

## Implementation Order

1. PostgreSQL, SQLAlchemy Async, Alembic, Redis, Celery, Docker Compose.
2. Database models and migrations for organization, project, taxonomy,
   documents, chunks, governance, and runtime records.
3. Repository and service layer.
4. Adapt current ingestion and RAG to PostgreSQL plus Chroma v2.
5. Keep current Agent v1 working; do not implement new business Agents.
6. After first-stage acceptance, the next independent task is
   `online_collection_agent`.
