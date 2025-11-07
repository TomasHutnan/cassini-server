"""Configuration management for the game server."""

import os
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Server settings
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Copernicus API credentials
    CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Game settings
    DEFAULT_MAP_RANGE: int = int(os.getenv("DEFAULT_MAP_RANGE", "200"))
    HEX_RESOLUTION: int = int(os.getenv("HEX_RESOLUTION", "12"))
    MAX_MAP_RANGE: int = int(os.getenv("MAX_MAP_RANGE", "5000"))

    @property
    def has_copernicus_credentials(self) -> bool:
        """Check if Copernicus credentials are configured."""
        return bool(self.CLIENT_ID and self.CLIENT_SECRET)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
