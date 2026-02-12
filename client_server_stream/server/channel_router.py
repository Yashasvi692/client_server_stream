from collections import defaultdict
import json

class ChannelRouter:
    def __init__(self):
        # channel_name -> set(ws)
        self.channels = defaultdict(set)
        # candidate_id -> set(ws)
        self.candidates = defaultdict(set)
        self.client_services = defaultdict(set)
        # candidate_id -> list(channel_name)
        self.candidate_channels = {}

    # Existing channel subscribe (unchanged behaviour)
    def subscribe(self, ws, channels):
        for ch in channels:
            self.channels[ch].add(ws)

    # New: subscribe to candidate(s)
    def subscribe_candidate(self, ws, candidate_ids):
        for cid in candidate_ids:
            self.candidates[cid].add(ws)

    def subscribe_service(self, candidate_id, services):
        self.client_services[candidate_id].update(services)

    # Unsubscribe a ws from both channels and candidates
    def unsubscribe(self, ws):
        for subs in self.channels.values():
            subs.discard(ws)
        for subs in self.candidates.values():
            subs.discard(ws)

    # Legacy emit by channel (keeps backward compatibility)
    async def emit(self, channel, message):
        for ws in list(self.channels[channel]):
            try:
                print("ROUTER EMIT:", channel, message)
                await ws.send_text(json.dumps(message))
            except Exception:
                pass

    # Broadcast to all channels
    async def broadcast(self, message):
        seen = set()
        for subs in self.channels.values():
            for ws in subs:
                if ws not in seen:
                    seen.add(ws)
                    try:
                        await ws.send_text(json.dumps(message))
                    except Exception:
                        pass

    # Register which channels should also receive a candidate's stream
    def register_candidate_channels(self, candidate_id, channels):
        if channels:
            self.candidate_channels[candidate_id] = list(channels)
        else:
            self.candidate_channels.pop(candidate_id, None)

    # Unregister candidate completely (cleanup)
    def unregister_candidate(self, candidate_id):
        # remove candidate mapping and candidate subscriptions
        self.candidate_channels.pop(candidate_id, None)
        if candidate_id in self.candidates:
            self.candidates.pop(candidate_id, None)

    # Emit to candidate subscribers, and also to any channel subscribers mapped to this candidate
    async def emit_candidate(self, candidate_id, message):
        seen = set()

        for ws in list(self.candidates.get(candidate_id, set())):
            if ws not in seen:
                seen.add(ws)
                await ws.send_text(json.dumps(message))


        # also send to channel subscribers that were registered for this candidate
        for ch in self.client_services.get(candidate_id, []):
            for ws in list(self.channels.get(ch, set())):
                try:
                    print(f"ROUTER EMIT CANDIDATE->CHANNEL: {candidate_id} -> {ch}", message)
                    await ws.send_text(json.dumps(message))
                except Exception:
                    pass

router = ChannelRouter()
