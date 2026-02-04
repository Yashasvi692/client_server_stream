from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import traceback

from .protocol import validate_message, error_message, Event, ProtocolError
from .auth import authenticate, AuthError
from .rate_limit import StreamRateLimiter, RateLimitError
from .stream_manager import StreamManager

app = FastAPI()

manager = StreamManager()
limiter = StreamRateLimiter()
from fastapi import FastAPI

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
            payload = msg["data"].get("payload")

            if event == Event.STREAM_START:
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
                        ws, stream_id, channel, payload
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

    async def emit(message: str):
        """
        Send plain-text observations to the client.
        Fail silently if the socket is already closed.
        """
        try:
            await ws.send_text(message)
        except Exception:
            pass

    await emit("Observer connected")
    await emit("Initializing server execution")

    try:
        # ---- Example observable execution ----
        # This is where you narrate real server work later

        await emit("Loading plugins")
        await asyncio.sleep(0.5)

        await emit("Starting execution")
        await asyncio.sleep(0.5)

        for i in range(1, 6):
            await emit(f"Running step {i}")
            await asyncio.sleep(1)

        await emit("Execution completed successfully")

    except Exception as e:
        # Stream the error BEFORE dying
        await emit("Unhandled exception occurred")
        await emit(str(e))

        # Optional: stream traceback line-by-line
        tb = traceback.format_exc().splitlines()
        for line in tb:
            await emit(line)

    finally:
        await emit("Execution ended")
        await ws.close()
