import asyncio
import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

# Simple in-memory broadcast: list of asyncio.Queue
_subscribers: list[asyncio.Queue] = []


async def broadcast(event_type: str, data: dict):
    message = json.dumps({"type": event_type, **data})
    dead = []
    for q in _subscribers:
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _subscribers.remove(q)


@router.get("/events")
async def event_stream():
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(queue)

    async def generate():
        try:
            while True:
                data = await queue.get()
                yield {"data": data}
        except asyncio.CancelledError:
            pass
        finally:
            if queue in _subscribers:
                _subscribers.remove(queue)

    return EventSourceResponse(generate())
