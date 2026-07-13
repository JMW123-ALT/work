import pytest

from app.services.agent import Evidence, run_agent


class FakeRetriever:
    def __init__(self, items):
        self.items = items
        self.calls = []

    def search(self, query: str, n_results: int = 5):
        self.calls.append({"query": query, "n_results": n_results})
        return self.items


class FakeLLM:
    def __init__(self):
        self.calls = []

    def chat(self, messages, temperature=0.3, max_tokens=1024):
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        user_content = messages[-1]["content"]
        if "输出 JSON" in user_content:
            return {
                "content": '{"intent":"planning","keywords":["秀洲区郊野公园","概念方案"],"style":"生态休闲风"}',
                "model": "fake",
                "mode": "fake",
            }
        if "传播文案" in user_content:
            return {
                "content": "LLM传播文案：来秀洲郊野公园，把城市脚步交还给田野。",
                "model": "fake",
                "mode": "fake",
            }
        if "方案设计" in user_content:
            return {
                "content": "LLM方案设计：一轴两环三片区，配置入口服务、亲子自然课堂、湿地栈道和田园市集。",
                "model": "fake",
                "mode": "fake",
            }
        if "文化考据" in user_content:
            return {
                "content": "LLM文化考据：围绕秀洲郊野公园的生态基底、田园游线和公共服务节点展开。",
                "model": "fake",
                "mode": "fake",
            }
        return {"content": "unused", "model": "fake", "mode": "fake"}


@pytest.mark.asyncio
async def test_run_agent_uses_llm_for_intent_review_design_and_marketing():
    llm = FakeLLM()
    result = await run_agent(
        "根据秀洲区郊野公园概念方案给我出一个方案",
        retriever=FakeRetriever(
            [
                Evidence(
                    text="秀洲区郊野公园概念方案提出生态湿地、田园游线、亲子活动和入口服务节点。",
                    source="doc://xiuzhou",
                    category="planning_doc",
                    culture_theme="秀洲区郊野公园概念方案",
                    confidence=0.92,
                    copyright_status="public_domain",
                    risk_level="low",
                )
            ]
        ),
        llm=llm,
    )

    assert result["status"] == "ok"
    assert result["intent"] == "planning"
    assert result["keywords"] == ["秀洲区郊野公园", "概念方案"]
    assert result["style"] == "生态休闲风"
    assert result["cultural_review"].startswith("LLM文化考据")
    assert result["design_plan"].startswith("LLM方案设计")
    assert result["marketing_copy"].startswith("LLM传播文案")
    assert result["llm_modes"] == {
        "intent": "fake",
        "cultural_review": "fake",
        "design": "fake",
        "marketing": "fake",
    }
    assert result["workflow"] == "langgraph"
    assert "LLM方案设计" in result["final_answer"]
    assert len(llm.calls) == 4
    assert "秀洲区郊野公园概念方案提出生态湿地" in llm.calls[1]["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_run_agent_generates_full_wenchuang_plan_with_evidence():
    retriever = FakeRetriever(
        [
            Evidence(
                text="敦煌藻井纹样常见莲花、卷草和几何秩序，可用于杯身主视觉。",
                source="dunhuang://zaojing",
                category="pattern",
                culture_theme="敦煌藻井",
                confidence=0.91,
                copyright_status="public_domain",
                risk_level="low",
            )
        ]
    )

    result = await run_agent(
        "敦煌保温杯文创，偏国潮厚重风，输出小红书文案",
        retriever=retriever,
    )

    assert result["status"] == "ok"
    assert result["intent"] == "copywriting"
    assert result["style"] == "国潮厚重风"
    assert result["evidence"][0]["source"] == "dunhuang://zaojing"
    assert "敦煌藻井" in result["cultural_review"]
    assert "保温杯" in result["design_plan"]
    assert "小红书" in result["marketing_copy"]
    assert "最终方案" in result["final_answer"]
    assert retriever.calls


@pytest.mark.asyncio
async def test_run_agent_stops_design_when_material_is_missing():
    result = await run_agent(
        "不存在素材的文创方案",
        retriever=FakeRetriever([]),
    )

    assert result["status"] == "need_more_material"
    assert result["evidence"] == []
    assert result["design_plan"] == ""
    assert result["marketing_copy"] == ""
    assert "资料不足" in result["final_answer"]


@pytest.mark.asyncio
async def test_run_agent_keeps_low_confidence_evidence_as_reviewable_draft():
    result = await run_agent(
        "根据秀洲区郊野公园概念方案给我出一个方案",
        retriever=FakeRetriever(
            [
                Evidence(
                    text="秀洲区郊野公园概念方案包含生态游线、田园场景和公共服务节点。",
                    source="doc://xiuzhou-low-score",
                    category="planning_doc",
                    culture_theme="秀洲区郊野公园概念方案",
                    confidence=0.36,
                    copyright_status="public_domain",
                    risk_level="low",
                )
            ]
        ),
        min_confidence=0.7,
    )

    assert result["status"] == "need_human_review"
    assert result["evidence"][0]["source"] == "doc://xiuzhou-low-score"
    assert result["design_plan"]
    assert result["marketing_copy"]
    assert any("低于阈值 0.70" in warning for warning in result["warnings"])
    assert "人工复核" in result["final_answer"]


@pytest.mark.asyncio
async def test_run_agent_marks_copyright_risk_for_human_review_but_keeps_draft():
    result = await run_agent(
        "某知名IP联名文创方案",
        retriever=FakeRetriever(
            [
                {
                    "text": "该素材授权状态不明，只可作为内部讨论参考。",
                    "source": "internal://ip-note",
                    "culture_theme": "授权素材",
                    "confidence": 0.88,
                    "copyright_status": "unknown",
                    "risk_level": "medium",
                }
            ]
        ),
    )

    assert result["status"] == "need_human_review"
    assert any("版权" in warning or "授权" in warning for warning in result["warnings"])
    assert result["design_plan"]
    assert result["marketing_copy"]
    assert "人工复核" in result["final_answer"]


@pytest.mark.asyncio
async def test_run_agent_blocks_cultural_safety_risk_before_retrieval():
    retriever = FakeRetriever(
        [
            Evidence(
                text="不应该被检索到",
                source="unused",
                confidence=0.9,
            )
        ]
    )

    result = await run_agent("恶搞烈士形象做低俗文创", retriever=retriever)

    assert result["status"] == "blocked"
    assert result["evidence"] == []
    assert result["design_plan"] == ""
    assert result["marketing_copy"] == ""
    assert retriever.calls == []
