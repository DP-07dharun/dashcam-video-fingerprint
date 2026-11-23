from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or a `.env` file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Dashcam Video-Fingerprint Service"

    # Supabase exposes a regular PostgreSQL connection string
    # (Project Settings -> Database -> Connection string). SQLite is used for local dev/tests.
    database_url: str = "sqlite:///./fingerprints.db"

    # HMAC key used to sign every fingerprint certificate. MUST be overridden in production.
    signing_secret: str = "dev-only-change-me"

    # Optional shared API key. When set, every /api route except /api/health requires X-API-Key.
    api_key: str | None = None

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    max_upload_mb: int = 500

    # Fingerprint tuning
    sample_interval_s: float = 0.5  # one perceptual hash every N seconds of video
    hamming_threshold: int = 10  # max differing bits (of 64) for two frames to "match"
    authentic_similarity: float = 0.95  # >= this share of matching samples -> same footage
    related_similarity: float = 0.40  # >= this -> same footage, but parts were altered
    max_offset_samples: int = 6  # alignment search window (handles trimmed starts)


@lru_cache
def get_settings() -> Settings:
    return Settings()
