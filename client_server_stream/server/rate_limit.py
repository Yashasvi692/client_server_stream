from collections import defaultdict


class RateLimitError(Exception):
    """Raised when a client exceeds its allowed stream quota."""


class StreamRateLimiter:
    """
    In-memory limiter for concurrent streams per API key.

    NOTE:
    - This is per-process.
    - Replace with Redis for multi-instance deployments.
    """

    def __init__(self):
        self._active_streams = defaultdict(int)

    def acquire(self, api_key: str, max_streams: int) -> None:
        """
        Attempt to reserve a stream slot.

        Raises:
            RateLimitError: if limit is exceeded
        """
        if self._active_streams[api_key] >= max_streams:
            raise RateLimitError(
                f"Max concurrent streams exceeded ({max_streams})"
            )

        self._active_streams[api_key] += 1

    def release(self, api_key: str) -> None:
        """
        Release a previously acquired stream slot.
        """
        if self._active_streams[api_key] > 0:
            self._active_streams[api_key] -= 1
