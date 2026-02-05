import asyncio
import websockets

URL = "wss://web-production-27a77.up.railway.app/observe?channels=homepage,button:1"

async def test():
    async with websockets.connect(URL) as ws:
        print("Connected!")

        while True:
            msg = await ws.recv()
            print("Received:", msg)

asyncio.run(test())
