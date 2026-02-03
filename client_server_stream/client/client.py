import asyncio
import json
import uuid
from typing import AsyncIterator, Dict, Optional

import websockets

from client_server_stream.server.protocol import (
    Event,
    build_message,
    validate_message,
)


class StreamClient:
    def __init__(self, url: str, api_key: Optional[str] = None):
        self.url = url
        self.api_key = api_key
        self._ws = None
        self._receiver_task = None
        self._streams: Dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def connect(self):
        if self._ws is not None:
            return

        async with self._lock:
            if self._ws is not None:
                return

            url = self.url
            if self.api_key:
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}api_key={self.api_key}"

            self._ws = await websockets.connect(url)
            self._receiver_task = asyncio.create_task(self._receiver_loop())

    async def _receiver_loop(self):
        async for raw in self._ws:
            msg = json.loads(raw)
            validate_message(msg)

            stream_id = msg["stream_id"]
            queue = self._streams.get(stream_id)
            if not queue:
                continue

            if msg["event"] == Event.STREAM_CHUNK:
                await queue.put(msg["data"]["payload"])
            elif msg["event"] == Event.STREAM_END:
                await queue.put(StopAsyncIteration)

    async def stream(self, payload, *, channel: str) -> AsyncIterator:
        await self.connect()

        stream_id = str(uuid.uuid4())
        queue = asyncio.Queue()
        self._streams[stream_id] = queue

        await self._ws.send(
            json.dumps(
                build_message(
                    event=Event.STREAM_START,
                    stream_id=stream_id,
                    channel=channel,
                    data={"payload": payload},
                )
            )
        )

        try:
            while True:
                item = await queue.get()
                if item is StopAsyncIteration:
                    break
                yield item 
        finally:
            self._streams.pop(stream_id, None)

    async def close(self):
        if self._ws:
            await self._ws.close()
