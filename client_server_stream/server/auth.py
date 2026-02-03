from typing import Dict


class AuthError(Exception):
    """Raised when API key authentication fails."""


# In-memory API key store (replaceable with DB / Redis later)
VALID_API_KEYS: Dict[str, Dict] = {
    "dev-key-123": {
        "client": "local-dev",
        "max_streams": 5,
    },
    "demo-key-456": {
        "client": "demo-user",
        "max_streams": 2,
    },
}


def authenticate(api_key: str | None) -> Dict:
    """
    Validate an API key and return client metadata.

    Raises:
        AuthError: if key is missing or invalid
    """
    if not api_key:
        raise AuthError("Missing API key")

    client_info = VALID_API_KEYS.get(api_key)
    if not client_info:
        raise AuthError("Invalid API key")

    return client_info
