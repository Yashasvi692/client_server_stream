from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import traceback

from .protocol import validate_message, error_message, Event, ProtocolError
from .auth import authenticate, AuthError
from .rate_limit import StreamRateLimiter, RateLimitError
from .stream_manager import StreamManager
from .channel_router import router
app = FastAPI()
manager = StreamManager()
limiter = StreamRateLimiter()

@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    api_key = ws.query_params.get("api_key")

    try:
        client_info = authenticate(api_key)
    except AuthError:
        await ws.close(code=1008)
        return

    max_streams = client_info.get("max_streams", 1)
    await ws.accept()

    active_streams = {}

    try:
        while True:
            msg = await ws.receive_json()
            print("Received message:", msg)

            try:
                validate_message(msg)
            except ProtocolError as e:
                await ws.send_json(
                    error_message(
                        stream_id=msg.get("stream_id"),
                        code="PROTOCOL_ERROR",
                        message=str(e),
                    )
                )
                continue

            event = msg["event"]
            stream_id = msg["stream_id"]
            channel = msg["channel"]
            payload = msg.get("data", {}).get("payload")
            plugin_name = msg.get("plugin", "llm_demo")
            print("PLUGIN:", plugin_name)
            print("CHANNEL:", channel)
            print("PAYLOAD:", payload)

            if not channel:
                await ws.send_json(
                    error_message(
                        stream_id=stream_id,
                        code="MISSING_CHANNEL",
                        message="Channel is required for streaming"
                    )
                )
                continue
    
            if event == "stream.start":
                if stream_id in active_streams:
                    continue

                try:
                    limiter.acquire(api_key, max_streams)
                except RateLimitError as e:
                    await ws.send_json(
                        error_message(
                            stream_id=stream_id,
                            code="RATE_LIMIT",
                            message=str(e),
                        )
                    )
                    continue

                task = asyncio.create_task(
                    manager.start_stream(
                        ws, stream_id,plugin_name, channel, payload
                    )
                )
                active_streams[stream_id] = task

            elif event == Event.STREAM_CANCEL:
                task = active_streams.pop(stream_id, None)
                if task:
                    task.cancel()
                    limiter.release(api_key)

    except WebSocketDisconnect:
        for task in active_streams.values():
            task.cancel()
            limiter.release(api_key)

@app.websocket("/observe")
async def observe_endpoint(ws: WebSocket):
    await ws.accept()

    channels_param = ws.query_params.get("channels")
    if not channels_param:
        await ws.send_text("No channel specified")
        await ws.close()
        return

    channels = [c.strip() for c in channels_param.split(",")]
    router.subscribe(ws, channels)

    await ws.send_text(f"Subscribed to: {', '.join(channels)}")

    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        router.unsubscribe(ws)
