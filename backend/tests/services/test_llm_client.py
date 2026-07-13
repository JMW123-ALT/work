from app.services.llm_client import LLMClient


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        assert kwargs["stream"] is False
        if self.calls == 1:
            raise RuntimeError("temporary failure")
        return _FakeCompletion("DeepSeek SDK answer")


class _FakeOpenAIClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": _FakeCompletions()})()


def test_llm_client_uses_openai_sdk_and_retries_once():
    openai_client = _FakeOpenAIClient()
    client = LLMClient(openai_client=openai_client, api_key="test-key", max_retries=2)

    result = client.chat([{"role": "user", "content": "hello"}])

    assert result == {
        "content": "DeepSeek SDK answer",
        "model": client.model,
        "mode": "deepseek",
    }
    assert openai_client.chat.completions.calls == 2


def test_llm_client_stream_yields_openai_sdk_chunks():
    class Delta:
        content = "片段"

    class StreamChoice:
        delta = Delta()

    class StreamCompletions:
        def create(self, **kwargs):
            assert kwargs["stream"] is True
            return [type("Chunk", (), {"choices": [StreamChoice()]})()]

    openai_client = type(
        "FakeClient",
        (),
        {"chat": type("Chat", (), {"completions": StreamCompletions()})()},
    )()
    client = LLMClient(openai_client=openai_client, api_key="test-key")

    assert list(client.stream_chat([{"role": "user", "content": "hello"}])) == ["片段"]
