import asyncio
from client_server_stream.client.client import StreamClient


async def main():
    client = StreamClient(
        url="wss://web-production-27a77.up.railway.app/ws",
        api_key="dev-key-123",
    )

    async for ch in client.stream("legacy", channel="text"):
        print(ch, end="")

    print("\nLEGACY DONE")


asyncio.run(main())
