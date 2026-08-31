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

    # Experimental LiNeP transport switch (see the LiNeP plan for context) -
    # off by default; the static host/port point at the linep-server already
    # running locally on this same machine, not a remote/dynamic cluster.
    linep_enabled: bool = False
    linep_host: str = "127.0.0.1"
    linep_port: int = 11435
    linep_timeout_seconds: float = 180.0

    class Config:
        env_file = ".env"


settings = Settings()
