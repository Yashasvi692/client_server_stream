from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import traceback
import uuid
from .protocol import validate_message, error_message, Event, build_message
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
            print("CREATING STREAM TASK")


            try:
                validate_message(msg)
            except Exception as e:
                print("VALIDATION ERROR:", e)
                traceback.print_exc()

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
            channels = msg.get("channels") or [msg.get("channel")]
            payload = msg.get("data", {}).get("payload")
            plugin_name = msg.get("plugin", "llm_demo")
            print("PLUGIN:", plugin_name)
            print("CHANNEL:", channels)
            print("PAYLOAD:", payload)

            if not channels:
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

                # Generate candidate_id / message_id (UUIDs)
                candidate_id = client_info["client"]                                                                                                                                                                                                
                message_id = uuid.uuid4().hex

                # Optionally, notify control socket that candidate was created (so client can display it)
                await ws.send_json(
                    build_message(
                        event=Event.STREAM_START,
                        stream_id=stream_id,
                        candidate_id=candidate_id,
                        message_id=message_id,
                        data={"info": "stream starting", "candidate_id": candidate_id, "message_id": message_id},
                    )
                )

                # schedule stream with candidate info
                task = asyncio.create_task(
                    manager.start_stream(None, stream_id, plugin_name, channels, payload, candidate_id=candidate_id, message_id=message_id)
                )

                active_streams[stream_id] = task

            elif event == "stream.cancel":
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
    print("OBSERVE SOCKET CONNECT ATTEMPT")
    await ws.accept()

    candidate_param = ws.query_params.get("candidate_id")
    print("OBSERVE CANDIDATE:", candidate_param)

    router.subscribe_candidate(ws, [candidate_param])
    router.subscribe_service(candidate_param, ["homepage"])


    print("OBSERVE CONNECTED:", candidate_param)

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        router.unsubscribe(ws)
