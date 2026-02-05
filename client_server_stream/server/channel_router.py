from collections import defaultdict

class ChannelRouter:
    def __init__(self):
        self.channels = defaultdict(set)

    def subscribe(self, ws, channels):
        for ch in channels:
            self.channels[ch].add(ws)

    def unsubscribe(self, ws):
        for subs in self.channels.values():
            subs.discard(ws)

    async def emit(self, channel, message):
        for ws in list(self.channels[channel]):
            try:
                await ws.send_text(message)
            except Exception:
                pass

    async def broadcast(self, message):
        seen = set()
        for subs in self.channels.values():
            for ws in subs:
                if ws not in seen:
                    seen.add(ws)
                    try:
                        await ws.send_text(message)
                    except Exception:
                        pass

router = ChannelRouter()