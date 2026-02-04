import asyncio
from .base import StreamPlugin

class DebugTextPlugin(StreamPlugin):
    name = "text"

    async def stream(self, payload):
        for i in range(5):
            yield f"chunk {i}\n"
            await asyncio.sleep(0.2)
