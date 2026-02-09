from fastapi.websockets import WebSocketState
from .protocol import Event, build_message
from .plugins.loader import discover_plugins
from .channel_router import router
import json

class StreamManager:
    def __init__(self):
        self.plugins = discover_plugins()
        print("PLUGINS LOADED:", self.plugins)
    async def start_stream(self, ws, stream_id, plugin_name, channels, payload):
        print("STREAM STARTED:", plugin_name, channels, payload)

        plugin = self.plugins.get(plugin_name)
        if not plugin:
            if ws and ws.application_state == WebSocketState.CONNECTED:
                await ws.send_json(
                    build_message(
                        event=Event.ERROR,
                        stream_id=stream_id,
                        data={
                            "code": "UNKNOWN_CHANNEL",
                            "message": f"No plugin '{plugin_name}'",
                        },
                    )
                )
            return

        # Normalize channels to list of strings
        if isinstance(channels, str):
            channels = [channels]

        async for chunk in plugin.stream(payload):

            # Control WS response (optional)
            if ws:
                await ws.send_json(
                    build_message(
                        event=Event.STREAM_CHUNK,
                        stream_id=stream_id,
                        data={"payload": chunk},
                    )
                )

            # Broadcast logic
            targets = set(channels)

            # Homepage acts as abstraction hub
            if "homepage" in channels:
                targets.update(router.channels.keys())

            print("EMITTING TO CHANNELS:", targets, "CHUNK:", chunk)

            for ch in targets:
                if isinstance(ch, str):
                    await router.emit(
                        ch,
                        build_message(
                            event=Event.STREAM_CHUNK,
                            stream_id=stream_id,
                            data={"payload": chunk},
                        ),
                    )

        # Stream end control message
        if ws:
            await ws.send_json(
                build_message(
                    event=Event.STREAM_END,
                    stream_id=stream_id,
                )
            )

        # Broadcast stream completion
        targets = set(channels)

        if "homepage" in channels:
            targets.update(router.channels.keys())

        for ch in targets:
            if isinstance(ch, str):
                await router.emit(
                    ch,
                    build_message(
                        event=Event.STREAM_END,
                        stream_id=stream_id,
                    ),
                )

