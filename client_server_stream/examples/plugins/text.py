import asyncio
from server.plugins.base import StreamPlugin


class TextStreamPlugin(StreamPlugin):
    name = "text"

    async def stream(self, payload: str):
        for char in str(payload):
            yield char
            await asyncio.sleep(0.1)
