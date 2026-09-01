"""Core configuration for Liara application."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    app_name: str = "Liara"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Database settings
    database_url: str = "sqlite:///./liara.db"
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8100

    # Experimental LiNeP transport switch (see the LiNeP-switch plan) - off
    # by default; the static host/port point at the linep-server already
    # running locally on this same machine, not a remote/dynamic cluster.
    linep_enabled: bool = False
    linep_host: str = "127.0.0.1"
    linep_port: int = 11435
    linep_timeout_seconds: float = 180.0

    # The shared .env carries ~13 other keys (smtp_*, *_password,
    # ollama_base_url, ...) that were never declared as fields here -
    # pydantic-settings rejects any undeclared key by default
    # (extra_forbidden), which had gone unnoticed only because nothing
    # actually imported/instantiated this Settings class before (see the
    # LiNeP-switch plan/commit history for the outage this caused).
    # Ignoring them is correct: this class only needs to own ITS OWN
    # declared fields, not validate every key that happens to live in
    # the same .env file for unrelated code.
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
