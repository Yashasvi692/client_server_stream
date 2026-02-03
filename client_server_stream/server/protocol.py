from typing import Any, Dict, Optional
from enum import Enum


PROTOCOL_VERSION = "streamkit/1.0"


class Event(str, Enum):
    STREAM_START = "stream.start"
    STREAM_CHUNK = "stream.chunk"
    STREAM_END = "stream.end"
    STREAM_CANCEL = "stream.cancel"
    ERROR = "error"


REQUIRED_FIELDS = {
    "protocol",
    "event",
    "stream_id",
    "channel",
    "data",
    "meta",
}


class ProtocolError(Exception):
    """Raised when a protocol violation occurs."""


def validate_message(message: Dict[str, Any]) -> None:
    """
    Validate an incoming or outgoing protocol message.

    Raises:
        ProtocolError: if message violates protocol rules
    """
    if not isinstance(message, dict):
        raise ProtocolError("Message must be a JSON object")

    missing = REQUIRED_FIELDS - message.keys()
    if missing:
        raise ProtocolError(f"Missing required fields: {missing}")

    if message["protocol"] != PROTOCOL_VERSION:
        raise ProtocolError(
            f"Invalid protocol version: {message['protocol']}"
        )

    try:
        Event(message["event"])
    except ValueError:
        raise ProtocolError(f"Invalid event type: {message['event']}")

    if message["stream_id"] is not None and not isinstance(message["stream_id"], str):
        raise ProtocolError("stream_id must be a string or null")

    if message["channel"] is not None and not isinstance(message["channel"], str):
        raise ProtocolError("channel must be a string or null")

    if not isinstance(message["data"], dict):
        raise ProtocolError("data must be an object")

    if not isinstance(message["meta"], dict):
        raise ProtocolError("meta must be an object")


def build_message(
    *,
    event: Event,
    stream_id: Optional[str] = None,
    channel: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build and validate a protocol-compliant message.
    """
    message = {
        "protocol": PROTOCOL_VERSION,
        "event": event.value,
        "stream_id": stream_id,
        "channel": channel,
        "data": data or {},
        "meta": meta or {},
    }

    validate_message(message)
    return message


def error_message(
    *,
    stream_id: Optional[str],
    code: str,
    message: str,
) -> Dict[str, Any]:
    """
    Build a standardized error message.
    """
    return build_message(
        event=Event.ERROR,
        stream_id=stream_id,
        data={
            "code": code,
            "message": message,
        },
    )
