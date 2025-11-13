"""API server configuration."""
import os
from typing import List


class APIConfig:
    """Configuration for the FastAPI server."""

    def __init__(self):
        self.host: str = os.getenv("API_HOST", "0.0.0.0")
        self.port: int = int(os.getenv("API_PORT", "8000"))

        # API Keys (required)
        api_keys_str = os.getenv("API_KEYS", "")
        if not api_keys_str:
            raise ValueError(
                "API_KEYS environment variable is required. "
                "Set it to a comma-separated list of valid API keys."
            )
        self.api_keys: List[str] = [k.strip() for k in api_keys_str.split(",") if k.strip()]

        # CORS origins (optional)
        cors_str = os.getenv("API_CORS_ORIGINS", "")
        self.cors_origins: List[str] = (
            [o.strip() for o in cors_str.split(",") if o.strip()]
            if cors_str else []
        )

        # Device state confirmation timeout
        self.device_state_timeout: float = float(
            os.getenv("API_DEVICE_STATE_TIMEOUT", "5.0")
        )


# Global config instance
_config: APIConfig | None = None


def get_config() -> APIConfig:
    """Get or create the API configuration singleton."""
    global _config
    if _config is None:
        _config = APIConfig()
    return _config
