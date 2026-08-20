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


settings = Settings()
