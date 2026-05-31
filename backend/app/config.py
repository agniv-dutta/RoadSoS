from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        enable_decoding=False,
    )

    app_name: str = "RoadSoS"
    version: str = "1.0.0"
    database_url: str = "sqlite+aiosqlite:///./roadsos.db"
    geoapify_places_api_key: str = ""
    geoapify_reverse_geocoding_api_key: str = ""
    geoapify_routing_api_key: str = ""
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None
    admin_secret_key: str = "roadsos_admin_2026"
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin for origin in self.cors_origins_raw.split(",") if origin]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings instance."""

    return Settings()
