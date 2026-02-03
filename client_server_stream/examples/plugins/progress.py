# client_server_stream/server/plugins/progress.py
import asyncio
from server.plugins.base import StreamPlugin


class ProgressStreamPlugin(StreamPlugin):
    name = "progress"

    async def stream(self, payload: dict):
        """
        payload example:
        {
            "total": 100,
            "delay": 0.05
        }
        """
        total = int(payload.get("total", 100))
        delay = float(payload.get("delay", 0.05))

        for i in range(1, total + 1):
            yield {
                "current": i,
                "total": total,
                "percent": int((i / total) * 100),
            }
            await asyncio.sleep(delay)
