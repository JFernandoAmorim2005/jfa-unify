"""
Configuração central da aplicação.
Lê variáveis de ambiente via pydantic-settings.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas do ambiente / ficheiro .env."""

    # --- Base de Dados ---
    database_url: str = "postgresql://jfaunify:devpassword123@localhost:5432/jfaunify_db"

    # --- Broker MQTT ---
    mqtt_adapter_type: str = "tuya"  # "tuya" ou "esp32"
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_tls_port: int = 8883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_client_id: str = "jfaunify-api"
    mqtt_ble_fallback_enabled: bool = False  # Apenas ESP32
    mqtt_local_cache_path: str = "/tmp/jfa_mqtt_cache.db"  # Apenas ESP32

    # --- Redis ---
    redis_url: str = "redis://localhost:6379"

    # --- Segurança ---
    secret_key: str = "change-me-in-production-must-be-32-chars-min"
    hmac_algorithm: str = "sha256"
    token_expiry_seconds: int = 3600

    # --- Tuya Hub ---
    tuya_hub_topic_prefix: str = "tuya/"
    tuya_access_id: str = ""
    tuya_access_secret: str = ""

    # --- Ambiente ---
    environment: str = "development"
    log_level: str = "DEBUG"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Retorna instância singleton das configurações."""
    return Settings()
