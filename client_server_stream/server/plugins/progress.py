# client_server_stream/server/plugins/progress.py
import asyncio
from .base import StreamPlugin

class DebugTextPlugin(StreamPlugin):
    channel = "text"

    async def on_stream_start(self, ctx):
        for i in range(5):
            await ctx.send_chunk(f"chunk {i}\n")
            await asyncio.sleep(0.2)
        await ctx.end()
