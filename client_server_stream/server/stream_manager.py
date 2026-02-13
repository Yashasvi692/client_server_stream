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

        if not candidate_id:
            raise ValueError("candidate_id required")

        if not message_id:
            message_id = uuid.uuid4().hex

        plugin = self.plugins.get(plugin_name)

        if not plugin:
            print("PLUGIN NOT FOUND:", plugin_name)
            return

        print("PLUGIN FOUND:", plugin)

        # Normalize channels
        if isinstance(channels, str):
            channels = [channels]

        try:
            print("STARTING PLUGIN STREAM...")

            async for chunk in plugin.stream(payload):
                print("PLUGIN CHUNK:", chunk)

                # Emit chunk to EACH channel
                for ch in channels:
                    chunk_msg = build_message(
                        event=Event.STREAM_CHUNK,
                        stream_id=stream_id,
                        candidate_id=candidate_id,
                        channel=ch,
                        message_id=message_id,
                        data={"payload": chunk},
                    )

                    if ws and ws.application_state == WebSocketState.CONNECTED:
                        await ws.send_json(chunk_msg)

                    await router.emit_candidate(candidate_id, chunk_msg)

        except Exception as e:
            print("PLUGIN STREAM ERROR:", e)

        finally:
            print("STREAM COMPLETE")

            for ch in channels:
                end_msg = build_message(
                    event=Event.STREAM_END,
                    stream_id=stream_id,
                    candidate_id=candidate_id,
                    channel=ch,
                    message_id=message_id,
                )

                if ws and ws.application_state == WebSocketState.CONNECTED:
                    await ws.send_json(end_msg)

                await router.emit_candidate(candidate_id, end_msg)
