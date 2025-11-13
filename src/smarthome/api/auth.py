"""API key authentication middleware and dependencies."""
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import get_config

# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify the API key from the request header.

    Args:
        api_key: The API key from the X-API-Key header

    Returns:
        The verified API key

    Raises:
        HTTPException: If the API key is missing or invalid
    """
    config = get_config()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Please provide an X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key not in config.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
