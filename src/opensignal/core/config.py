from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OPENSIGNAL_",
        extra="ignore",
    )

    service_name: str = "opensignal-api"
    environment: str = "development"
    log_level: str = "INFO"
    openfda_base_url: str = "https://api.fda.gov/drug/event.json"
    openfda_api_key: str | None = None
    openfda_max_attempts: int = 4
    openfda_backoff_seconds: float = 1.0
    data_dir: Path = Path("data")


@lru_cache
def get_settings() -> Settings:
    return Settings()
