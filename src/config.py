"""ACIT Gateway configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Razorpay test-mode credentials
    RAZORPAY_KEY_ID: str = Field(..., description="Razorpay test key ID (rzp_test_*)")
    RAZORPAY_KEY_SECRET: str = Field(..., description="Razorpay test key secret")
    RAZORPAY_WEBHOOK_SECRET: str = Field(..., description="Razorpay webhook secret")

    # JWT secret for agent identity (Vault)
    JWT_SECRET: str = Field(..., min_length=32, description="JWT signing secret (>=32 chars)")

    # API key for service-to-service auth
    API_KEY: str = Field(..., description="Service-to-service API key")

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./data/acit.db",
        description="SQLite database URL",
    )

    # Chaos engineering
    CHAOS_ENABLED: bool = Field(default=False, description="Enable chaos injection")
    CHAOS_FAILURE_RATE: float = Field(
        default=0.05, ge=0.0, le=1.0, description="Chaos failure rate (0-1)"
    )

    # MCP integration
    MCP_ENABLED: bool = Field(default=False, description="Enable MCP server")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Log level")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Module-level instance for convenience
settings = get_settings()
