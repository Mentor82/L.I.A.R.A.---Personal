"""Core configuration for Liara application."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    app_name: str = "Liara"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database settings
    database_url: str = "sqlite:///./liara.db"
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8100

    class Config:
        env_file = ".env"
        # The shared .env carries many keys other code reads directly via
        # os.environ (smtp_*, *_password, ollama_base_url, ...) that were
        # never declared as fields here - pydantic-settings rejects those by
        # default (extra_forbidden), which had gone unnoticed only because
        # nothing actually imported/instantiated this Settings class before.
        # Ignoring them is correct: this class only needs to own ITS OWN
        # declared fields, not validate every key that happens to live in
        # the same .env file for unrelated code.
        extra = "ignore"


settings = Settings()
