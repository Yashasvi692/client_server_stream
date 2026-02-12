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
        """
        Start a streaming session.

        IMPORTANT ARCHITECTURE RULES:
        - candidate_id represents CLIENT identity.
        - Services/channels are managed separately by router.
        - Streaming should NEVER change subscription state.
        """

        print("STREAM STARTED:", plugin_name, channels, payload)

        # Candidate ID must come from client identity (not channels)
        if not candidate_id:
            raise ValueError("candidate_id must be provided by client identity")

        if not message_id:
            message_id = uuid.uuid4().hex

        plugin = self.plugins.get(plugin_name)
        if not plugin:
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

        # Normalize channels (informational only, not subscription control)
        if isinstance(channels, str):
            channels = [channels]

        # STREAM EXECUTION
        try:
            async for chunk in plugin.stream(payload):
                chunk_msg = build_message(
                    event=Event.STREAM_CHUNK,
                    stream_id=stream_id,
                    candidate_id=candidate_id,
                    message_id=message_id,
                    data={"payload": chunk},
                )

                # Optional control socket echo
                if ws and ws.application_state == WebSocketState.CONNECTED:
                    await ws.send_json(chunk_msg)

                # Router handles who actually receives it
                await router.emit_candidate(candidate_id, chunk_msg)

        except Exception as e:
            print("STREAM ERROR:", e)

        # STREAM END MESSAGE
        end_msg = build_message(
            event=Event.STREAM_END,
            stream_id=stream_id,
            candidate_id=candidate_id,
            message_id=message_id,
        )

        if ws and ws.application_state == WebSocketState.CONNECTED:
            await ws.send_json(end_msg)

        await router.emit_candidate(candidate_id, end_msg)
