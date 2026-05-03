from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INCIDENT_", env_file=".env")

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://incident:incident@localhost:5432/incidents"
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "incident_signals"
    mongo_collection: str = "signals"
    nats_url: str = "nats://localhost:4222"
    nats_subject: str = "signals.raw"

    rate_limit_capacity: int = 20
    rate_limit_refill_per_second: float = 5.0
    max_in_flight_signals: int = 500

    slack_webhook_url: str | None = None
    pagerduty_routing_key: str | None = None
    pagerduty_events_url: str = "https://events.pagerduty.com/v2/enqueue"
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_sender: str = "incidents@example.com"
    email_to: str = "oncall@example.com"


app_settings = AppSettings()
