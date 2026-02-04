import asyncio
import json
import uuid
from typing import AsyncIterator, Optional

import websockets

from client_server_stream.server.protocol import (
    Event,
    build_message,
    validate_message,
)

_STREAM_END = object()


class StreamTransport:
    """
    INTERNAL transport layer.

    Responsibilities:
    - WebSocket connection management
    - Protocol send/receive
    - Stream multiplexing by stream_id
    """

    def __init__(self, url: str, api_key: Optional[str] = None):
        self._url = url
        self._api_key = api_key

        self._ws = None
        self._receiver_task = None
        self._streams: dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def connect(self):
        async with self._lock:
            if self._ws is None:
                url = self._url
                if self._api_key:
                    sep = "&" if "?" in url else "?"
                    url = f"{url}{sep}api_key={self._api_key}"

                self._ws = await websockets.connect(url)

            if self._receiver_task is None or self._receiver_task.done():
                self._receiver_task = asyncio.create_task(self._receiver_loop())

    async def _receiver_loop(self):
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                    validate_message(msg)

                    msg_type = msg.get("type")
                    stream_id = msg.get("stream_id")

                    # Ignore control / ack messages
                    if not msg_type or not stream_id:
                        continue

                    queue = self._streams.get(stream_id)
                    if not queue:
                        continue

                    if msg_type == Event.STREAM_CHUNK.value:
                        await queue.put(msg["data"]["payload"])

                    elif msg_type == Event.STREAM_END.value:
                        await queue.put(_STREAM_END)
                        self._streams.pop(stream_id, None)

                except Exception as e:
                    print("[StreamTransport] receiver error:", e)

        except Exception as e:
            print("[StreamTransport] receiver loop stopped:", e)
        finally:
            # force reconnect on next use
            self._ws = None

    async def open_stream(self, *, channel: str, payload) -> AsyncIterator:
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
                if item is _STREAM_END:
                    break
                yield item
        finally:
            self._streams.pop(stream_id, None)

    async def close(self):
        if self._ws:
            await self._ws.close()
            self._ws = None
