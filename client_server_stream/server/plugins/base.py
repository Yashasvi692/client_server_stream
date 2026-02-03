from abc import ABC, abstractmethod
from typing import AsyncIterator, Any


class StreamPlugin(ABC):
    """
    Base class for all stream plugins.
    """

    name: str  # REQUIRED, must be unique

    @abstractmethod
    async def stream(self, payload: Any) -> AsyncIterator[Any]:
        pass
