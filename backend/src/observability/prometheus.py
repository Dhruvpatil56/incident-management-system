from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from fastapi import APIRouter, Request, Response

try:  # pragma: no cover - real path validated in container runtime
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
except ModuleNotFoundError:  # pragma: no cover - local fallback for dev/tests
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class _DummyMetric:
        def labels(self, **_kwargs):
            return self

        def inc(self, _v: float = 1.0):
            return None

        def dec(self, _v: float = 1.0):
            return None

        def observe(self, _v: float):
            return None

        def set(self, _v: float):
            return None

    def Counter(*_args, **_kwargs):
        return _DummyMetric()

    def Gauge(*_args, **_kwargs):
        return _DummyMetric()

    def Histogram(*_args, **_kwargs):
        return _DummyMetric()

    def generate_latest():
        return b"# prometheus_client not installed in this runtime\n"

router = APIRouter()

# HTTP/API
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)

# Ingestion path
signals_ingested_total = Counter(
    "signals_ingested_total",
    "Total accepted signals",
)
signals_rejected_total = Counter(
    "signals_rejected_total",
    "Total rejected signals",
    ["reason"],
)
nats_publish_total = Counter(
    "nats_publish_total",
    "Successful NATS publishes",
)
nats_publish_failures_total = Counter(
    "nats_publish_failures_total",
    "Failed NATS publishes",
)
queue_inflight_signals = Gauge(
    "queue_inflight_signals",
    "Current in-flight signal operations",
)
queue_lag_estimate = Gauge(
    "queue_lag_estimate",
    "Approximate consumer lag estimate",
)

# Consumer/debounce/pipeline
consumer_messages_total = Counter(
    "consumer_messages_total",
    "Messages processed by consumer",
)
consumer_processing_duration_seconds = Histogram(
    "consumer_processing_duration_seconds",
    "Consumer processing latency",
)
debounce_dropped_total = Counter(
    "debounce_dropped_total",
    "Duplicate incidents dropped by debounce",
)
incident_created_total = Counter(
    "incident_created_total",
    "Created incidents",
)

# Workflow/RCA
incident_state_transitions_total = Counter(
    "incident_state_transitions_total",
    "Incident state transition attempts",
    ["from_state", "to_state", "result"],
)
rca_submissions_total = Counter(
    "rca_submissions_total",
    "RCA submissions",
)
rca_validation_failures_total = Counter(
    "rca_validation_failures_total",
    "RCA validation failures",
)
mttr_seconds = Histogram(
    "mttr_seconds",
    "Incident MTTR in seconds",
    buckets=(30, 60, 120, 300, 600, 1800, 3600, 7200, 14400, 28800, 86400),
)

# DB reliability
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query latency",
    ["db", "operation"],
)
db_errors_total = Counter(
    "db_errors_total",
    "Database operation errors",
    ["db", "operation"],
)
db_retry_attempts_total = Counter(
    "db_retry_attempts_total",
    "Database retry attempts",
    ["db", "operation"],
)


def observe_http(request: Request, status_code: int, started_at: float) -> None:
    path = request.url.path
    method = request.method
    http_requests_total.labels(method=method, path=path, status=str(status_code)).inc()
    http_request_duration_seconds.labels(method=method, path=path).observe(
        max(time.perf_counter() - started_at, 0.0)
    )


@contextmanager
def db_timing(db: str, operation: str) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    except Exception:
        db_errors_total.labels(db=db, operation=operation).inc()
        raise
    finally:
        db_query_duration_seconds.labels(db=db, operation=operation).observe(
            max(time.perf_counter() - started, 0.0)
        )


@router.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
