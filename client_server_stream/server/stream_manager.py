from fastapi.websockets import WebSocketState
from .protocol import Event, build_message
from .plugins.loader import discover_plugins
from .channel_router import router
import uuid


class StreamManager:
    def __init__(self):
        self.plugins = discover_plugins()
        print("PLUGINS LOADED:", self.plugins)

    async def start_stream(
        self,
        ws,
        stream_id,
        plugin_name,
        channels,
        payload,
        candidate_id=None,
        message_id=None,
    ):
        print("STREAM STARTED:", plugin_name, channels, payload)

        # Candidate identity required
        if not candidate_id:
            raise ValueError("candidate_id required")

        if not message_id:
            message_id = uuid.uuid4().hex

        plugin = self.plugins.get(plugin_name)

        if not plugin:
            print("PLUGIN NOT FOUND:", plugin_name)
            if ws and ws.application_state == WebSocketState.CONNECTED:
                await ws.send_json(
                    build_message(
                        event=Event.ERROR,
                        stream_id=stream_id,
                        candidate_id=candidate_id,
                        message_id=message_id,
                        data={
                            "code": "UNKNOWN_PLUGIN",
                            "message": f"No plugin '{plugin_name}'",
                        },
                    )
                )
            return

        print("PLUGIN FOUND:", plugin)

        # Normalize channels list
        if isinstance(channels, str):
            channels = [channels]

        channel_tag = channels[0] if channels else "homepage"

        try:
            print("STARTING PLUGIN STREAM...")

            async for chunk in plugin.stream(payload):
                print("PLUGIN CHUNK:", chunk)

                chunk_msg = build_message(
                    event=Event.STREAM_CHUNK,
                    stream_id=stream_id,
                    candidate_id=candidate_id,
                    channel=channel_tag,   # <-- CRITICAL FIX
                    message_id=message_id,
                    data={"payload": chunk},
                )

                # Send back on control socket if present
                if ws and ws.application_state == WebSocketState.CONNECTED:
                    await ws.send_json(chunk_msg)

                # Emit via router
                await router.emit_candidate(candidate_id, chunk_msg)

        except Exception as e:
            print("PLUGIN STREAM ERROR:", e)

            error_msg = build_message(
                event=Event.ERROR,
                stream_id=stream_id,
                candidate_id=candidate_id,
                channel=channel_tag,
                message_id=message_id,
                data={"message": str(e)},
            )

            await router.emit_candidate(candidate_id, error_msg)

        finally:
            print("STREAM COMPLETE")

            end_msg = build_message(
                event=Event.STREAM_END,
                stream_id=stream_id,
                candidate_id=candidate_id,
                channel=channel_tag,
                message_id=message_id,
            )

            if ws and ws.application_state == WebSocketState.CONNECTED:
                await ws.send_json(end_msg)

            await router.emit_candidate(candidate_id, end_msg)
