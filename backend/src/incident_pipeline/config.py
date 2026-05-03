from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INCIDENT_", env_file=".env")

    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50
    redis_socket_timeout: int = 2
    redis_health_check_interval: int = 30

    database_url: str = "postgresql://localhost:5432/incidents"

    debounce_window_seconds: int = 30

    cache_default_ttl: int = 300
    cache_stampede_beta: float = 4.0
    cache_list_ttl: int = 30
    cache_rca_stats_ttl: int = 900

    rca_min_length: int = 20
    rca_max_length: int = 5000


settings = Settings()