from .protocol import Event, build_message
from .plugins.loader import discover_plugins
from .channel_router import router

class StreamManager:
    def __init__(self):
        self.plugins = discover_plugins()
        print("PLUGINS LOADED:", self.plugins)

    async def start_stream(self, ws, stream_id, plugin_name, channel, payload):
        print("STREAM STARTED:", plugin_name, channel, payload)
        plugin = self.plugins.get(plugin_name)
        if not plugin:
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
        print("STREAM STARTED:", plugin_name, channel, payload)
        async for chunk in plugin.stream(payload):
            await ws.send_json(
                build_message(
                    event=Event.STREAM_CHUNK,
                    stream_id=stream_id,
                    channel=channel,
                    data={"payload": chunk},
                )
            )
            print("EMITTING TO CHANNEL:", channel, "CHUNK:", chunk)
            await router.emit(channel, chunk)

        await ws.send_json(
            build_message(
                event=Event.STREAM_END,
                stream_id=stream_id,
            )
        )
        await router.emit(channel, "[STREAM COMPLETE]")

