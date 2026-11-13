import asyncio
import json
import os
from collections.abc import AsyncIterator

import httpx


class LLMError(RuntimeError):
    pass


async def stream_reply(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    model = os.getenv("LLM_MODEL", "qwen2.5:3b")
    key = os.getenv("LLM_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    payload = {"model": model, "messages": messages, "stream": True, "max_tokens": 160}
    try:
        async with asyncio.timeout(90), httpx.AsyncClient(timeout=httpx.Timeout(60, connect=5)) as client:
            async with client.stream(
                "POST", f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    event = json.loads(data)
                    if "error" in event:
                        raise LLMError("LLM returned a streaming error")
                    choices = event["choices"]
                    if choices:
                        token = choices[0]["delta"].get("content")
                        if isinstance(token, str) and token:
                            yield token
    except (TimeoutError, httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise LLMError("LLM endpoint is unavailable") from exc
    raise LLMError("LLM stream ended unexpectedly")
