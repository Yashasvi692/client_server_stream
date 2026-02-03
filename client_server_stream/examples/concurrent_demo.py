import asyncio
from client_server_stream.client import StreamClient


async def text_stream(client: StreamClient):
    print("\n--- Text Stream ---")
    async for chunk in client.stream(
        payload="Streaming text concurrently!",
        channel="text",
    ):
        print(chunk, end="", flush=True)
    print("\n--- Text Stream Done ---")


async def progress_stream(client: StreamClient):
    print("\n--- Progress Stream ---")
    async for update in client.stream(
        payload={"total": 10, "delay": 0.2},
        channel="progress",
    ):
        print(f"Progress: {update['percent']}%")
    print("--- Progress Stream Done ---")


async def main():
    client = StreamClient(
        "ws://localhost:8000/ws",
        api_key="dev-key-123",
    )


    # Run BOTH streams concurrently on the SAME connection
    await asyncio.gather(
        text_stream(client),
        progress_stream(client),
    )

    await client.close()


asyncio.run(main())
