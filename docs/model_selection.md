# 文创 Agent 模型选型建议

更新时间：2026-07-08

本文件用于给文创 Agent 选择国内可用模型。当前项目数据库由同事单独维护，因此这里重点给出模型层建议，后续数据库接入时按本方案配置 embedding、rerank 和回答模型。

## 1. 推荐总架构

文创 Agent 不建议只用一个大模型硬答，推荐采用三层模型链路：

```text
文档/图片/视频素材
-> 向量模型 Embedding
-> 向量库初召回 Chroma / Milvus / PGVector
-> 召回重排 Rerank
-> 回答组织模型 LLM
-> Guardrails / 人工复核
```

原因：

- 文创项目最怕“文化幻觉”，必须先检索史料再生成。
- 多模态素材多，图片纹样、器物图、展陈图不能只靠文本检索。
- 初召回追求“别漏”，重排追求“别乱”，回答模型负责“组织成可读方案”。

## 2. 最推荐组合

### 先给结论：最终选择方案

结合你的要求图，项目同时覆盖：

- To B 文创生产：IP 设计助手、非遗纹样创作、策展方案、产品企划、短视频脚本。
- To C 文旅消费：虚拟文博讲解员、文创种草推荐、数字藏品创作、景区虚拟 NPC。
- 多智能体协作：需求解析、视觉生成、文案润色、市场分析联合工作。
- 工具插件：文生图、多模态解析、联网检索、文档导出、多智能体分工。
- 标准工作流：意图识别、混合检索、LLM 创意生成、工具调用、内容校验、标准化交付、用户记忆。

所以最终不选“纯文本便宜方案”，也不选“一上来全旗舰高价方案”。最终选择：

```text
最终方案：阿里多模态检索 + 阿里重排 + DeepSeek 组织回答 + 百度/文心高质量复核可选

向量模型：阿里百炼 qwen3-vl-embedding
召回/重排：Chroma/Milvus 初召回 + 阿里百炼 qwen3-rerank
图文混合重排升级：qwen3-vl-rerank
回答组织模型：DeepSeek deepseek-v4-flash
高质量复核模型：ERNIE 5.0，仅用于最终稿/专家复核
文生图工具：通义万相 / qwen-image
多模态解析：qwen-vl / ERNIE-4.5-Turbo-VL
联网检索：先用普通搜索 API，后续再接专用搜索增强
```

说明：DeepSeek 官方兼容名 `deepseek-chat` 将在 2026-07-24 后废弃，后续项目配置建议直接写 `deepseek-v4-flash`。

选择理由：

- 你的项目一定会有纹样图、壁画图、产品图，多模态向量必须提前考虑。
- 回答生成会被多 Agent 放大调用次数，主回答模型必须便宜。
- 文创项目需要文化严谨性，最终稿保留一个高质量复核模型比全程用贵模型更划算。
- 阿里在多模态 embedding / rerank 链路上更适合“图文混合素材库”；DeepSeek 在回答生成成本上更适合开发和高频 Demo。

一句话版本：

> 用阿里解决“找得准”，用 DeepSeek 解决“答得便宜”，用 ERNIE 5.0 解决“最终复核稳”。

### 方案 A：均衡推荐，最适合当前项目

| 层级 | 推荐模型 | 作用 | 理由 |
|---|---|---|---|
| 多模态向量 | 阿里百炼 `qwen3-vl-embedding` | 文本、图片、视频统一向量化 | 支持中英日韩法德等多语种，支持图片和视频，适合纹样、壁画、器物图检索 |
| 召回重排 | 阿里百炼 `qwen3-rerank` / `qwen3-vl-rerank` | 对 Top-N 史料精排 | 纯文本用 qwen3-rerank；图文混合用 qwen3-vl-rerank |
| 回答模型 | DeepSeek-V4-Flash 或 ERNIE 4.5 Turbo | 组织文化考据、文创方案和营销文案 | 成本低，中文输出够用，适合高频调用 |
| 高质量复核 | ERNIE 5.0 / GLM-5.2 | 专家版复核、最终方案润色 | 更适合复杂推理、严肃文博语境和最终交付 |

### 方案 B：低成本文本优先

| 层级 | 推荐模型 | 作用 | 理由 |
|---|---|---|---|
| 文本向量 | 智谱 `Embedding-3` 或百度 `Embedding-V1` | 文本史料向量化 | 价格低，适合先跑文本 RAG |
| 召回重排 | 百度 `bce-reranker-base` | 文本重排 | 价格低，适合先做 MVP |
| 回答模型 | DeepSeek-V4-Flash | 生成回答 | 极低成本，适合开发阶段和大量测试 |

### 方案 C：文博/国企合规优先

| 层级 | 推荐模型 | 作用 | 理由 |
|---|---|---|---|
| 向量 | 百度 `Embedding-V1` / 阿里 `qwen3-vl-embedding` | 文本或多模态检索 | 百度/阿里云企业平台合规链路更成熟 |
| 重排 | 百度 `bce-reranker-base` 或阿里 `qwen3-rerank` | 史料精排 | 便于和云厂商 IAM、审计、企业账号体系集成 |
| 回答模型 | ERNIE 5.0 / ERNIE 4.5 Turbo | 文博类中文回答 | 中文、政企、文博类场景更稳妥 |

## 3. 向量模型对比

| 模型 | 模态 | 价格参考 | 能力 | 适合场景 | 建议 |
|---|---|---:|---|---|---|
| 阿里 `qwen3-vl-embedding` | 文本 + 图片 + 视频 | 文本约 0.0007 元/千 Token；图片/视频约 0.0018 元/千 Token | 默认 2560 维，文本最长 32K，支持图片和视频 | 纹样图、壁画图、器物图、图文混合检索 | 首选多模态向量 |
| 阿里 `tongyi-embedding-vision-plus-2026-03-06` | 文本 + 图片 + 视频 | 约 0.0005 元/千 Token | 支持多图，最多 64 张；维度可选 | 成本敏感的图文检索 | 低成本多模态备选 |
| 智谱 `Embedding-3` | 文本 | 0.5 元/百万 Token | 256-2048 维可选，上下文 8K | 文本史料、策展文档、营销文案 | 文本 RAG 性价比高 |
| 智谱 `Embedding-2` | 文本 | 0.5 元/百万 Token | 1024 维，上下文 8K | 稳定文本语义搜索 | 可作为低成本备选 |
| 百度 `Embedding-V1` | 文本 | 0.0005 元/千 Token | 文本向量，用于检索、推荐、知识挖掘 | 政企/百度云体系项目 | 合规项目备选 |

结论：

- 你这个文创 Agent 有纹样图、壁画图、产品图，长期应选 `qwen3-vl-embedding`。
- 如果当前只做文档、PDF、文本史料，可以先用 `Embedding-3` 或 `Embedding-V1` 降成本。
- 等数据库同事接入图片素材后，再切多模态向量。

## 4. 召回/重排模型对比

这里要区分两步：

```text
初召回：向量库 Top 50 / Top 100
重排：Rerank 从 Top 50 选 Top 5-8
```

| 模型 | 模态 | 价格参考 | 能力 | 适合场景 | 建议 |
|---|---|---:|---|---|---|
| 阿里 `qwen3-rerank` | 文本 | 约 0.7 元/百万 Token | 支持 100+ 语言，最多 500 个文档 | 文本史料精排 | 首选文本重排 |
| 阿里 `qwen3-vl-rerank` | 文本 + 图片 + 视频 | 文本约 0.7 元/百万 Token；图片约 1.8 元/百万 Token | 支持文本、图片、视频混合排序 | 纹样图、产品图、文档混合召回 | 多模态检索时首选 |
| 百度 `bce-reranker-base` | 文本 | 0.0005 元/千 Token | 文本相关性重排 | 低成本文本 RAG | MVP 阶段很合适 |
| 本地 BGE Reranker | 文本 | API 成本为 0，需本地算力 | 可私有化，数据不出内网 | 内网、涉密、预算固定项目 | 后期私有化可考虑 |

结论：

- 当前阶段：用向量库初召回即可，先别急着加复杂 rerank。
- Demo 稳定后：接 `qwen3-rerank`，把 Top 50 压到 Top 8。
- 图文混合库上线后：接 `qwen3-vl-rerank`。

## 5. 回答组织模型对比

回答模型负责把检索证据组织成：

- 文化溯源
- 可用元素
- 禁用/慎用点
- 文创设计方案
- 小红书/抖音/电商文案
- 人工复核提示

| 模型 | 价格参考 | 能力 | 优点 | 缺点 | 建议 |
|---|---:|---|---|---|---|
| DeepSeek-V4-Flash | 百度千帆参考：输入 0.001 元/千 Token，输出 0.002 元/千 Token | 通用生成、代码、长文本组织 | 成本低，适合高频 Demo 和开发调试 | 文博严谨性需要 Guardrails 和复核 | 当前开发首选 |
| ERNIE 4.5 Turbo | 百度千帆参考：输入 0.0008 元/千 Token，输出 0.0032 元/千 Token | 中文生成、营销文案、政企场景 | 中文表达稳，成本低 | 复杂推理弱于旗舰模型 | 文案/普通问答推荐 |
| ERNIE 5.0 | 百度千帆参考：输入 0.006 元/千 Token，输出 0.024 元/千 Token | 更强推理和复杂任务 | 文博、政企、合规项目更稳 | 成本较高 | 专家复核/最终稿使用 |
| GLM-5.2 | Z.ai 参考：输入 $1.4/百万 Token，输出 $4.4/百万 Token | 高质量中文组织、复杂推理 | 适合复杂方案、严肃回答 | 美元计价，平台链路需确认 | 高质量备选 |
| GLM-4.7-FlashX | Z.ai 参考：输入 $0.07/百万 Token，输出 $0.4/百万 Token | 轻量生成 | 很便宜 | 复杂文化考据不建议单独依赖 | 简单摘要/草稿可用 |
| Qwen3.5-27B | 百度千帆参考：输入 0.0006 元/千 Token，输出 0.0048 元/千 Token | 中文通用生成、长上下文 | 性价比好 | 具体版本和平台需对齐 | 阿里/千问生态备选 |

结论：

- 你现在做 MVP：`DeepSeek-V4-Flash` 或 `ERNIE 4.5 Turbo`。
- 要给老师/客户看最终效果：生成后再用 `ERNIE 5.0` 或 `GLM-5.2` 做一次复核润色。
- 不建议一开始全程用旗舰模型，成本会被多 Agent 流程放大。

## 6. 针对本项目的最终推荐

## 6.1 按应用场景补充模型策略

### To B 文创生产场景

场景：

- IP 设计助手
- 非遗纹样创作
- 策展方案撰写
- 文创产品企划
- 短视频宣传脚本生成

推荐模型链路：

```text
qwen3-vl-embedding
-> qwen3-rerank
-> deepseek-v4-flash
-> ERNIE 5.0 复核
```

原因：

- To B 更看重可交付方案质量和史实准确。
- IP 设计、策展、产品企划都需要先检索知识库，再组织成结构化方案。
- 最终交付给客户/老师/企业时，建议加一次高质量复核。

### To C 文旅消费场景

场景：

- 虚拟文博讲解员
- 文创种草推荐
- 数字藏品创作
- 景区互动虚拟 NPC

推荐模型链路：

```text
qwen3-vl-embedding
-> qwen3-rerank
-> deepseek-v4-flash
```

原因：

- To C 更看重响应速度和调用成本。
- 用户问答频率高，不适合每次都调用高价旗舰模型。
- 文化问答必须保留低置信度拦截，避免虚构讲解。

### 多智能体协同场景

场景：

- 需求解析 Agent
- 视觉生成 Agent
- 文案润色 Agent
- 市场分析 Agent

推荐分工：

| Agent | 模型/工具 | 原因 |
|---|---|---|
| 需求解析 Agent | 规则 + 小模型或 deepseek-v4-flash | 意图分类不需要高价模型 |
| 文化考据 Agent | qwen3-rerank + deepseek-v4-flash | 先精排证据，再组织考据 |
| 创意设计 Agent | deepseek-v4-flash + 通义万相/qwen-image | 文案与视觉草图联动 |
| 营销优化 Agent | deepseek-v4-flash | 高频文案生成，成本优先 |
| 复核 Agent | ERNIE 5.0 | 只处理最终稿或高风险内容 |

## 6.2 按工具插件补充模型策略

| 工具插件 | 推荐模型/服务 | 是否第一阶段必须接 | 说明 |
|---|---|---:|---|
| 文生图插件 | 通义万相 / qwen-image | 否 | 先保留接口；等文案链路稳定后再接 |
| 产品效果图 | qwen-image / ERNIE 图像生成 | 否 | 成本按张计费，Demo 后期再接 |
| IP 形象草图 | 通义万相 / qwen-image | 否 | 适合演示，但不是 Agent 主链路刚需 |
| 古籍 OCR | 百度 OCR / 文心 OCR / 通用 OCR | 否 | 数据库同事处理素材时更需要 |
| 图片元素提取 | qwen-vl / ERNIE-4.5-Turbo-VL | 第二阶段 | 用于纹样、壁画、器物图结构化入库 |
| 联网检索 | 搜索 API + LLM 摘要 | 第二阶段 | 只补行业热点、政策、节日节点，不替代史料库 |
| 文档导出 | python-docx / markdown | 是 | 当前就可以做，成本低 |
| 表格生成 | openpyxl / xlsxwriter | 是 | 项目计划、报价、产品清单可直接生成 |

## 6.3 按标准自动化工作流映射模型

| 工作流节点 | 当前建议 | 最终建议 |
|---|---|---|
| 意图识别 | 规则识别 | 规则 + deepseek-v4-flash 兜底 |
| 混合检索 | Mock / Chroma 文本检索 | qwen3-vl-embedding + Chroma/Milvus |
| 召回重排 | 暂不接 | qwen3-rerank；图文混合用 qwen3-vl-rerank |
| LLM 创意生成 | deepseek-v4-flash | deepseek-v4-flash 主生成 |
| 工具自动调用 | 先用手写工具节点 | 后续接文生图、导出、联网检索 |
| 内容校验 | 规则 Guardrails | 规则 + ERNIE 5.0 高风险复核 |
| 标准化输出 | Prompt 模板 | Prompt 模板 + JSON Schema |
| 用户记忆 | 暂不做 | SQLite / Redis / 用户画像表 |

## 6.4 评分矩阵

评分规则：5 分最好，1 分最弱。

| 方案 | 成本 | 多模态能力 | 文创适配 | 工程落地 | 合规稳定 | 总评 |
|---|---:|---:|---:|---:|---:|---:|
| 纯 DeepSeek + 文本 Embedding | 5 | 2 | 3 | 5 | 3 | 18 |
| 智谱 Embedding-3 + GLM 全家桶 | 4 | 3 | 4 | 4 | 4 | 19 |
| 百度千帆 Embedding + ERNIE | 3 | 4 | 4 | 4 | 5 | 20 |
| 阿里 qwen3-vl-embedding + qwen3-rerank + DeepSeek | 5 | 5 | 5 | 4 | 4 | 23 |
| 全程 ERNIE 5.0 / 旗舰模型 | 2 | 5 | 5 | 3 | 5 | 20 |

最终选择：

```text
阿里 qwen3-vl-embedding
+ 阿里 qwen3-rerank
+ DeepSeek deepseek-v4-flash
+ ERNIE 5.0 最终复核
```

这是当前最均衡的一套。

### 为什么不选全程 ERNIE 5.0？

因为你的流程是多 Agent 链路，一次请求可能调用多次模型。如果全程用旗舰模型，成本会被放大。ERNIE 5.0 更适合最后复核，而不是每个节点都用。

### 为什么不选纯 DeepSeek？

DeepSeek 适合回答组织和文案生成，但你的项目需要多模态知识库：纹样图、壁画图、器物图、产品图。纯 DeepSeek 解决不了图文向量检索。

### 为什么最终选阿里多模态检索？

因为你的需求图明确包含：

- 文生图插件
- 图片传统元素提取
- 产品效果图
- IP 形象草图
- 多模态解析工具

这些都要求向量层能处理图片/视频/文本统一检索。

## 6.5 最终落地版本

### 最终唯一方案一页版

这个项目最终就按这一套走：

| 层级 | 最终选择 | 作用 | 接入时间 |
|---|---|---|---|
| 向量模型 | 阿里百炼 `qwen3-vl-embedding` | 文本、图片、视频素材统一向量化 | 数据库素材接入后 |
| 向量库 | `Chroma` 起步，后续可换 `Milvus` | Top 50 / Top 100 初召回 | 现在已有 Chroma，可先保留 |
| 文本重排 | 阿里百炼 `qwen3-rerank` | 文本史料精排 | 文本知识库稳定后 |
| 多模态重排 | 阿里百炼 `qwen3-vl-rerank` | 图文混合证据精排 | 图片/视频素材入库后 |
| 主回答模型 | DeepSeek `deepseek-v4-flash` | 文化考据、产品企划、营销文案、脚本组织 | 现在就可以配置 |
| 复核模型 | 百度 `ERNIE 5.0` | 高风险文化内容、最终稿、人审前复核 | 展示/交付阶段 |
| 文生图工具 | 通义万相 / `qwen-image` | IP 草图、纹样、产品效果图 | 第二阶段以后 |
| 多模态解析 | `qwen-vl` / `ERNIE-4.5-Turbo-VL` | 古籍 OCR 后的图像理解、传统元素提取 | 第二阶段以后 |

不建议现在就全接，因为数据库还没拉下来。当前最该做的是把 `UnifiedLLM` 先接到 `deepseek-v4-flash`，让 Agent 的回答链路变成真实模型输出；等数据库同事的知识库代码到位后，再接 `qwen3-vl-embedding` 和 rerank。

### 第一阶段：现在就做

```text
回答模型：DeepSeek deepseek-v4-flash
向量模型：暂用 Mock / 等数据库同事接入
召回模型：Chroma 初召回
重排模型：暂不接
复核模型：规则 Guardrails
```

目标：让 Agent 真实回答，成本低，方便调试。

### 第二阶段：数据库接入后

```text
向量模型：qwen3-vl-embedding
向量库：Chroma 或 Milvus
重排模型：qwen3-rerank
回答模型：deepseek-v4-flash
```

目标：文本史料、纹样图、产品图都能召回。

### 第三阶段：项目展示/验收前

```text
复核模型：ERNIE 5.0
视觉工具：通义万相 / qwen-image
多模态解析：qwen-vl / ERNIE-4.5-Turbo-VL
```

目标：最终稿更稳，视觉生成能力可演示。

### 开发阶段

```text
Embedding：Mock / 文本 Embedding-3
Rerank：先不接，向量 Top 5 足够
LLM：DeepSeek-V4-Flash
```

目标：便宜、快、能跑通流程。

### Demo 阶段

```text
Embedding：qwen3-vl-embedding
Rerank：qwen3-rerank
LLM：ERNIE 4.5 Turbo 或 DeepSeek-V4-Flash
```

目标：能展示“图文素材 + 检索证据 + 文创回答”。

### 正式交付阶段

```text
Embedding：qwen3-vl-embedding
Rerank：qwen3-vl-rerank
LLM：ERNIE 5.0 / GLM-5.2
Guardrails：版权、史实、争议史料、人审标签
```

目标：降低文化幻觉和版权风险。

## 7. 成本控制建议

文创 Agent 是多节点流程，成本不是只看一次回答。

一次完整请求可能包含：

```text
意图识别 1 次
检索 query embedding 1 次
Rerank 1 次
文化考据 1 次
设计生成 1 次
营销文案 1 次
风控/复核 1 次
```

所以建议：

- 意图识别用规则或小模型，不要用大模型。
- 文本史料先切片，避免把整篇文档丢给回答模型。
- Rerank 只对 Top 30-50 做，不要对全库做。
- 文化考据和设计生成分开，避免模型把“史实”和“创意”混在一起。
- 最终复核才用贵模型。

## 8. 本项目落地顺序

现在代码已经有：

- `UnifiedLLM`
- `ChromaRetriever`
- `WenchuangState`
- `/chat`
- `/chat/stream`
- Mock demo cases

下一步建议：

1. 先配置 `LLM_API_KEY`，用 `DeepSeek-V4-Flash` 或 `ERNIE 4.5 Turbo` 跑真实回答。
2. 等同事数据库完成后，先接文本 embedding。
3. 再接 `qwen3-rerank`。
4. 最后接 `qwen3-vl-embedding` 和 `qwen3-vl-rerank` 做图文混合检索。

## 9. 参考来源

- 阿里百炼 Multimodal Embedding 文档：https://help.aliyun.com/zh/model-studio/multimodal-embedding-api-reference
- 阿里百炼向量与重排序说明：https://www.alibabacloud.com/help/zh/model-studio/embedding-rerank-model
- 阿里百炼模型价格页：https://www.alibabacloud.com/help/en/model-studio/model-pricing
- DeepSeek 模型与价格页：https://api-docs.deepseek.com/quick_start/pricing
- 智谱 Embedding-3 文档：https://docs.bigmodel.cn/cn/guide/models/embedding/embedding-3
- 智谱 Embedding-2 文档：https://docs.bigmodel.cn/cn/guide/models/embedding/embedding-2
- 智谱 Z.ai 价格页：https://docs.z.ai/guides/overview/pricing
- 百度千帆价格页：https://cloud.baidu.com/doc/qianfan/s/Jm8r1826a
- 百度千帆模型服务计费页：https://cloud.baidu.com/doc/qianfan/s/wmh4sv6ya
