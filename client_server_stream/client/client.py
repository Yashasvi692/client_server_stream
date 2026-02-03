import asyncio
from typing import Any, Callable, Optional, AsyncIterator

from .transport import StreamTransport


OnChunk = Callable[[Any], None]
OnEnd = Callable[[], None]
OnError = Callable[[Exception], None]


class StreamClient:
    """
    PUBLIC client API.

    This client supports:
    1. Push-based streaming (addon-style)  ✅ preferred
    2. Async iteration (legacy / internal) ⚠️ temporary
    """

    def __init__(self, url: str, api_key: Optional[str] = None):
        self._transport = StreamTransport(url, api_key)

    # ------------------------------------------------------------------
    # NEW: ADDON-STYLE PUSH API (THIS IS STEP 5)
    # ------------------------------------------------------------------

    def start_stream(
        self,
        *,
        channel: str,
        payload: Any,
        on_chunk: OnChunk,
        on_end: Optional[OnEnd] = None,
        on_error: Optional[OnError] = None,
    ) -> None:
        """
        Start a stream without exposing async iteration.

        This method:
        - returns immediately
        - runs the stream in the background
        - pushes data via callbacks
        """

        asyncio.create_task(
            self._run_stream(
                channel=channel,
                payload=payload,
                on_chunk=on_chunk,
                on_end=on_end,
                on_error=on_error,
            )
        )

    async def _run_stream(
        self,
        *,
        channel: str,
        payload: Any,
        on_chunk: OnChunk,
        on_end: Optional[OnEnd],
        on_error: Optional[OnError],
    ) -> None:
        """
        INTERNAL worker that consumes the transport stream
        and dispatches events to callbacks.
        """
        try:
            await self._transport.connect()

            async for item in self._transport.open_stream(
                channel=channel,
                payload=payload,
            ):
                on_chunk(item)

            if on_end:
                on_end()

        except Exception as e:
            if on_error:
                on_error(e)
            else:
                # Fail silently by default (addon-friendly behavior)
                pass

    # ------------------------------------------------------------------
    # LEGACY API (KEEP FOR NOW — DO NOT REMOVE YET)
    # ------------------------------------------------------------------

    async def stream(self, payload, *, channel: str) -> AsyncIterator:
        """
        Legacy pull-based API.
        Will be removed in a later step.
        """
        async for item in self._transport.open_stream(
            channel=channel,
            payload=payload,
        ):
            yield item

    async def close(self):
        await self._transport.close()
