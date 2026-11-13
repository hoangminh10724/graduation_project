"""Run the prompt evaluation cases against the configured real LLM endpoint."""
import asyncio
import json
from time import perf_counter

from app.llm import stream_reply
from app.prompts import coaching_prompt

CASES = [
    ("A2", "I goes to school by bus."),
    ("A2", "Yesterday I eat noodles."),
    ("A2", "My sister is 15 years."),
    ("A2", "I like music."),
    ("A2", "I don't understand."),
    ("B1", "I have visited Da Nang last year."),
    ("B1", "My city has many traffic."),
    ("B1", "I went to the market. Assessment hint: Practice /θ/."),
    ("B1", "I think the movie was interesting."),
    ("B2", "If I would have more time, I'd volunteer."),
]


async def main() -> None:
    for level, text in CASES:
        started = perf_counter()
        first_token = None
        chunks = []
        async for token in stream_reply([
            {"role": "system", "content": coaching_prompt(level, "Daily life")},
            {"role": "user", "content": text},
        ]):
            if first_token is None:
                first_token = perf_counter() - started
            chunks.append(token)
        reply = "".join(chunks).strip()
        print(json.dumps({
            "level": level, "input": text, "reply": reply,
            "words": len(reply.split()), "within_40_words": len(reply.split()) <= 40,
            "first_token_seconds": first_token,
            "elapsed_seconds": perf_counter() - started,
        }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
