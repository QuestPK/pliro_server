import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")

    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Redis Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # API Configuration
    API_V1_STR: str = "/api/v1"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 86400  # 1 day in seconds

    # Allow extra fields to be ignored
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'  # This will allow extra environment variables without raising an error
    )


settings = Settings()