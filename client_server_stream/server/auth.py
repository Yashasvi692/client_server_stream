from typing import Dict


class AuthError(Exception):
    """Raised when API key authentication fails."""


# In-memory API key store (replaceable with DB / Redis later)
VALID_API_KEYS = {
    "user1-key": {
        "client": "user1",
        "max_streams": 5,
    },
    "user2-key": {
        "client": "user2",
        "max_streams": 5,
    },
    "user3-key": {
        "client": "user3",
        "max_streams": 5,
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
