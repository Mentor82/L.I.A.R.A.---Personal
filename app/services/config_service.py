"""Config Service - Lädt System-Konfiguration mit Fallback."""
from sqlalchemy.orm import Session
from api.models.base_models import SystemConfig
from typing import Optional


class ConfigService:
    """Service für System-Konfiguration."""
    
    def __init__(self, db: Session):
        self.db = db
        self._config_cache: Optional[SystemConfig] = None
    
    def get_config(self) -> SystemConfig:
        """
        Lädt System-Config aus DB oder erstellt Defaults.
        Verwendet Caching für Performance.
        """
        if self._config_cache is None:
            self._config_cache = self.db.query(SystemConfig).first()
            
            if self._config_cache is None:
                # Create default config
                self._config_cache = SystemConfig(
                    default_model="llama3.2:3b",
                    max_tokens=2000,
                    temperature=70,
                    system_prompt=None,
                    guest_message_limit=20,
                    guest_message_length=500,
                    user_message_limit=100,
                    rate_limit_window=60,
                    web_search_enabled=True,
                    location_services_enabled=True,
                    guest_mode_enabled=True,
                    registration_enabled=True,
                    data_retention_days=30,
                    search_history_retention_days=7,
                    location_retention_days=30,
                    auto_delete_enabled=True,
                    ollama_host="http://localhost:11434",
                    ollama_timeout=120,
                    ollama_pull_on_start=False
                )
                self.db.add(self._config_cache)
                self.db.commit()
                self.db.refresh(self._config_cache)
        
        return self._config_cache
    
    def reload_config(self) -> SystemConfig:
        """Force reload der Config (z.B. nach Update)."""
        self._config_cache = None
        return self.get_config()
    
    def get_system_prompt(self) -> Optional[str]:
        """Holt globalen System Prompt."""
        config = self.get_config()
        # SQLAlchemy ORM object - attribute ist bereits Python str
        prompt: Optional[str] = config.system_prompt  # type: ignore[assignment]
        return prompt
    
    def get_default_model(self) -> str:
        """Holt Default AI Model."""
        config = self.get_config()
        model: str = config.default_model  # type: ignore[assignment]
        return model
    
    def get_temperature(self) -> float:
        """Holt Temperature (konvertiert von 0-100 zu 0.0-1.0)."""
        config = self.get_config()
        temp: int = config.temperature  # type: ignore[assignment]
        return temp / 100.0
    
    def get_max_tokens(self) -> int:
        """Holt Max Tokens."""
        config = self.get_config()
        tokens: int = config.max_tokens  # type: ignore[assignment]
        return tokens
    
    def get_guest_limits(self) -> dict:
        """Holt Guest-Mode Limits."""
        config = self.get_config()
        return {
            "message_limit": config.guest_message_limit,
            "message_length": config.guest_message_length
        }
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Prüft ob Feature aktiviert ist."""
        config = self.get_config()
        # SQLAlchemy ORM object - attributes sind bereits Python bool
        web_search: bool = config.web_search_enabled  # type: ignore[assignment]
        location: bool = config.location_services_enabled  # type: ignore[assignment]
        guest: bool = config.guest_mode_enabled  # type: ignore[assignment]
        registration: bool = config.registration_enabled  # type: ignore[assignment]
        
        feature_map = {
            "web_search": web_search,
            "location": location,
            "guest_mode": guest,
            "registration": registration
        }
        return feature_map.get(feature, False)


def get_config_service(db: Session) -> ConfigService:
    """Dependency Injection für ConfigService."""
    return ConfigService(db)
