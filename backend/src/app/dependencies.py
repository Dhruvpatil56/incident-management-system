from __future__ import annotations

import asyncio

from fastapi import Depends, Request

from alerting.email import EmailAlert
from alerting.pagerduty import PagerDutyAlert
from alerting.router import AlertRouter
from alerting.slack import SlackAlert
from app.config import app_settings
from ingestion.rate_limiter import TokenBucket
from ingestion.producer import SignalProducer
from incident_pipeline.cache.hotcache import Cache
from incident_pipeline.db.store import IncidentStore
from incident_pipeline.debounce.deduper import Debouncer
from incident_pipeline.models import Severity
from incident_pipeline.pipeline import IncidentPipeline
from incident_pipeline.rca.policy import RcaPolicy
from observability.metrics import ThroughputCounter
from signals.store import InMemorySignalStore


def _ensure_bootstrapped(app) -> None:
    if hasattr(app.state, "pipeline"):
        return
    raise RuntimeError("application state is not bootstrapped; check app startup")


def get_pipeline(request: Request) -> IncidentPipeline:
    _ensure_bootstrapped(request.app)
    return request.app.state.pipeline


def get_signal_store(request: Request) -> InMemorySignalStore:
    _ensure_bootstrapped(request.app)
    return request.app.state.signal_store


def get_rate_limiter(request: Request) -> TokenBucket:
    _ensure_bootstrapped(request.app)
    return request.app.state.rate_limiter


def get_alert_router(request: Request) -> AlertRouter:
    _ensure_bootstrapped(request.app)
    return request.app.state.alert_router


def get_signal_producer(request: Request) -> SignalProducer:
    _ensure_bootstrapped(request.app)
    return request.app.state.signal_producer


def get_incident_store(request: Request) -> IncidentStore:
    _ensure_bootstrapped(request.app)
    return request.app.state.incident_store


def bootstrap_defaults(app) -> None:
    store = IncidentStore(app.state.db)
    app.state.incident_store = store
    app.state.signal_store = InMemorySignalStore()
    app.state.pipeline = IncidentPipeline(
        debouncer=Debouncer(app.state.redis),
        rca_policy=RcaPolicy(),
        cache=Cache(app.state.redis),
        store_fn=store.create,
    )
    app.state.rate_limiter = TokenBucket(
        capacity=app_settings.rate_limit_capacity,
        refill_per_second=app_settings.rate_limit_refill_per_second,
    )
    app.state.ingest_semaphore = asyncio.Semaphore(app_settings.max_in_flight_signals)
    app.state.throughput = ThroughputCounter()
    app.state.signal_producer = SignalProducer(app.state.nats, app_settings.nats_subject)
    app.state.alert_router = AlertRouter(
        {
            # P0 -> PagerDuty + Slack; P1 -> Slack; P2 -> Email
            Severity.p0: [
                PagerDutyAlert(
                    app_settings.pagerduty_routing_key,
                    app_settings.pagerduty_events_url,
                ),
                SlackAlert(app_settings.slack_webhook_url),
            ],
            Severity.p1: [SlackAlert(app_settings.slack_webhook_url)],
            Severity.p2: [
                EmailAlert(
                    app_settings.smtp_host,
                    app_settings.smtp_port,
                    app_settings.smtp_sender,
                    app_settings.email_to,
                )
            ],
        }
    )
