from fastapi.websockets import WebSocketState
from .protocol import Event, build_message
from .plugins.loader import discover_plugins
from .channel_router import router

class StreamManager:
    def __init__(self):
        self.plugins = discover_plugins()
        print("PLUGINS LOADED:", self.plugins)
        
    def get_all_channels(self):
        return list(router.get_all_channels())
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

        print("STREAM STARTED:", plugin_name, channels, payload)

        async for chunk in plugin.stream(payload):
            if ws:
                await ws.send_json(
                    build_message(
                        event=Event.STREAM_CHUNK,
                        stream_id=stream_id,
                        data={"payload": chunk},
                    )
                )

            targets = set(channels)

            if "homepage" in channels:
                targets.update(router.get_all_channels())

            for ch in targets:
                await router.emit(ch, chunk)

        if ws:
            await ws.send_json(
                build_message(
                    event=Event.STREAM_END,
                    stream_id=stream_id,
                )
            )

        targets = set(channels)

        if "homepage" in channels:
            targets.update(router.get_all_channels())

        for ch in targets:
            await router.emit(ch, "[STREAM COMPLETE]")



