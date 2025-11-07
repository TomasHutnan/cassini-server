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

    # Authentication settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

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
