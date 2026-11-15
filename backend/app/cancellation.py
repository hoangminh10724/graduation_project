"""Cooperative cancellation of external AI I/O, never of a database write thread."""
import asyncio
from time import monotonic

from anyio import CancelScope
from starlette.concurrency import run_in_threadpool

from .requests import stop_reason


class AIStopped(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class CancellationGuard:
    interval = 0.25

    def __init__(self, bind, record_id: int):
        self.bind = bind
        self.record_id = record_id
        self.checked_at = float("-inf")
        self.reason = None
        self.lock = asyncio.Lock()

    async def check(self, *, force: bool = False) -> None:
        async with self.lock:
            if force or monotonic() - self.checked_at >= self.interval:
                self.reason = await run_in_threadpool(stop_reason, self.bind, self.record_id)
                self.checked_at = monotonic()
            if self.reason is not None:
                raise AIStopped(self.reason)

    async def run(self, awaitable):
        task = asyncio.ensure_future(awaitable)
        try:
            while True:
                await self.check()
                done, _ = await asyncio.wait({task}, timeout=self.interval)
                if done:
                    await self.check()
                    return task.result()
        finally:
            with CancelScope(shield=True):
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)


async def guarded_stream(source, guard: CancellationGuard):
    # Keep the upstream generator's timeout/cancel scopes on one task across yields.
    queue = asyncio.Queue(maxsize=1)

    async def produce():
        try:
            async for token in source:
                await queue.put(token)
        finally:
            with CancelScope(shield=True):
                await source.aclose()

    producer = asyncio.create_task(produce())

    async def receive():
        getter = asyncio.create_task(queue.get())
        try:
            done, _ = await asyncio.wait({getter, producer}, return_when=asyncio.FIRST_COMPLETED)
            if getter in done:
                return "token", getter.result()
            if not queue.empty():
                return "token", queue.get_nowait()
            # A producer timeout can fire while backpressure blocks queue.put,
            # outside the generator's yield. Never leave the consumer waiting forever.
            if producer.cancelled():
                raise TimeoutError("Upstream stream stopped while waiting for consumption")
            producer.result()
            return "end", None
        finally:
            if not getter.done():
                getter.cancel()
            await asyncio.gather(getter, return_exceptions=True)

    try:
        while True:
            kind, value = await guard.run(receive())
            if kind == "end":
                return
            yield value
    finally:
        with CancelScope(shield=True):
            if not producer.done():
                producer.cancel()
            await asyncio.gather(producer, return_exceptions=True)
