import asyncio
import json

import httpx
import pytest

from app import llm


@pytest.mark.parametrize("complete", [True, False])
def test_openai_compatible_stream(monkeypatch, complete):
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.test/v1")
    monkeypatch.setenv("LLM_MODEL", "tutor")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    messages = [{"role": "user", "content": "Hello"}]
    original_client = httpx.AsyncClient

    def handler(request):
        assert str(request.url) == "http://llm.test/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["model"] == "tutor"
        assert payload["stream"] and payload["messages"] == messages
        body = 'data: {"choices":[{"delta":{"content":"Hi"}}]}\n\n'
        if complete:
            body += "data: [DONE]\n\n"
        return httpx.Response(200, text=body)

    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: original_client(
        transport=httpx.MockTransport(handler), **kwargs
    ))

    async def collect():
        return [token async for token in llm.stream_reply(messages)]

    if complete:
        assert asyncio.run(collect()) == ["Hi"]
    else:
        with pytest.raises(llm.LLMError, match="ended unexpectedly"):
            asyncio.run(collect())
