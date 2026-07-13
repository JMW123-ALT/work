# 文创 Agent 流程

文创 Agent 是后端内部服务，代码位置：

```text
backend/app/services/agent.py
backend/app/api/v1/agent.py
```

它不再作为独立服务运行，也不再通过另一个端口做 HTTP 检索适配。检索统一走当前后端内部的 `rag_service.search()`，数据来自：

```text
backend/data/vector_store.sqlite3
backend/data/chroma/
```

## 主流程

```mermaid
flowchart TD
    A["用户输入文创需求"] --> B["需求解析 intent_node"]
    B --> C["前置风控 pre_guardrails_node"]
    C -->|高风险| Z["最终输出 blocked"]
    C -->|通过| D0["DeepSeek 需求解析 llm_intent_node"]
    D0 --> D["内部检索 rag_service.search"]
    D -->|无候选资料| E["资料不足 need_more_material"]
    D -->|有低置信度候选| R["可讨论草案 need_human_review"]
    D -->|有高置信度资料| F["后置风控 post_guardrails_node"]
    R --> F
    F --> G["文化考据 cultural_review_node"]
    E --> G
    G -->|资料不足/拦截| Z
    G -->|可继续| H["创意设计 design_node"]
    H --> I["营销优化 marketing_node"]
    I --> Z["最终输出 final_node"]
```

## 状态

| 状态 | 含义 | 处理 |
|---|---|---|
| `ok` | 检索到足够史料且无重大风险 | 完整生成考据、设计、营销 |
| `need_more_material` | 无史料或置信度不足 | 不生成方案，提示补充素材 |
| `need_human_review` | 低置信度候选、版权不明、存在争议或疑似商用 IP | 可生成草案，但标注人工复核 |
| `blocked` | 命中文化安全高风险表达 | 直接停止 |

## 核心原则

- 有史料再生成。
- 低置信度可生成讨论草案，但必须标注人工核验。
- 争议史料和版权风险必须标注人工复核。
- 数据库逻辑留在 `vector_store` 和 `rag_service`，Agent 只消费 Evidence。
- Agent 编排使用 LangGraph，LLM 调用通过 OpenAI SDK 兼容 DeepSeek。
