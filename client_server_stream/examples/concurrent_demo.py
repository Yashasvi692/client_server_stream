import asyncio
from client_server_stream.client import StreamClient


async def main():
    client = StreamClient(
        "wss://web-production-27a77.up.railway.app/ws",
        api_key="dev-key-123",
    )

    print("\n--- Text Stream ---")
    print("\n--- Progress Stream ---")

    done = asyncio.Event()
    remaining = 2

    def mark_done():
        nonlocal remaining
        remaining -= 1
        if remaining == 0:
            done.set()

    client.start_stream(
        channel="text",
        payload="Streaming text concurrently!",
        on_chunk=lambda c: print(c, end="", flush=True),
        on_end=lambda: (print("\n--- Text Stream Done ---"), mark_done()),
        on_error=lambda e: (print("Text error:", e), mark_done()),
    )

    client.start_stream(
        channel="progress",
        payload={"total": 10, "delay": 0.2},
        on_chunk=lambda u: print(f"Progress: {u['percent']}%"),
        on_end=lambda: (print("--- Progress Stream Done ---"), mark_done()),
        on_error=lambda e: (print("Progress error:", e), mark_done()),
    )

    await done.wait()
    await client.close()


asyncio.run(main())
