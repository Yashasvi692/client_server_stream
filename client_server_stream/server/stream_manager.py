from fastapi.websockets import WebSocketState
from .protocol import Event, build_message
from .plugins.loader import discover_plugins
from .channel_router import router
import uuid

class StreamManager:
    def __init__(self):
        self.plugins = discover_plugins()
        print("PLUGINS LOADED:", self.plugins)

    async def start_stream(self, ws, stream_id, plugin_name, channels, payload, candidate_id=None, message_id=None):
        """
        Start a streaming session.

        candidate_id/message_id: If provided, use them. Otherwise generate UUIDs.
        channels: legacy channels list (optional) — if provided we register candidate->channels mapping so channel subscribers also receive the stream.
        """
        print("STREAM STARTED:", plugin_name, channels, payload)

        # Ensure IDs exist
        # Determine candidate_id properly
        if candidate_id is None:
            if channels:
                # If homepage broadcast, keep candidate_id as homepage
                if "homepage" in channels:
                    candidate_id = "homepage"
                # Single channel
                elif len(channels) == 1:
                    candidate_id = channels[0]
                # Multiple explicit channels
                else:
                    candidate_id = channels[0]  # pick primary channel
            else:
                candidate_id = uuid.uuid4().hex

        if message_id is None:
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

        # Normalize channels to list of strings
        if isinstance(channels, str):
            channels = [channels]

        # Register candidate->channels if channels provided (backwards compat)
        if channels:
            # Special case: "homepage" means broadcast to all current channels
            broadcast = False

            if "homepage" in channels:
                broadcast = True
                broadcast_channels = list(router.channels.keys())
            else:
                broadcast_channels = channels

            router.register_candidate_channels(candidate_id, broadcast_channels)
        try:
            async for chunk in plugin.stream(payload):
                # Build the chunk message (include candidate_id & message_id)
                chunk_msg = build_message(
                    event=Event.STREAM_CHUNK,
                    stream_id=stream_id,
                    candidate_id=candidate_id,
                    message_id=message_id,
                    data={"payload": chunk},
                )

                # If ws exists (control socket) also send control messages (optional)
                if ws:
                    await ws.send_json(chunk_msg)

                # Emit to candidate subscribers (primary)
                await router.emit_candidate(candidate_id, chunk_msg)

            # After stream finishes, send STREAM_END message
            end_msg = build_message(
                event=Event.STREAM_END,
                stream_id=stream_id,
                candidate_id=candidate_id,
                message_id=message_id,
            )

            if ws:
                await ws.send_json(end_msg)

            await router.emit_candidate(candidate_id, end_msg)

        finally:
            # Cleanup mapping so future streams don't accidentally broadcast
            router.unregister_candidate(candidate_id)
