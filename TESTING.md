# IMS Testing Guide (Current Stack)

## Purpose

This document explains:
- why testing exists in this repo,
- how to run each test layer,
- what results to expect when the system is healthy.

It reflects the current structure:
- Backend code/tests in `backend/`
- Frontend code in `frontend/`
- Full runtime stack in `compose.yaml`
- Observability via Prometheus + Grafana

## Test Layers

1. Unit/Service tests (fast, local, backend-focused)
2. API tests (FastAPI routes, lifespan-aware)
3. Full stack smoke tests (Docker Compose)
4. Observability validation (Prometheus/Grafana targets + dashboard)

## 1) Backend Unit + API Tests

Run from repo root:

```bash
python -m pytest backend/tests -q
```

What to expect:
- All tests pass (current baseline: `32 passed`).
- Warnings about `datetime.utcnow()` may appear; they are non-blocking for now.

Run with verbose output:

```bash
python -m pytest backend/tests -v
```

Run a single file:

```bash
python -m pytest backend/tests/test_api.py -v
```

## 2) Backend Coverage (Optional)

```bash
python -m pytest backend/tests --cov=backend/src -v
```

What to expect:
- Coverage summary for backend modules.
- Use this before submission to identify untested branches.

## 3) Full Stack Validation (Docker Compose)

Start everything:

```bash
docker compose up -d --build
```

Services expected:
- `backend` (FastAPI)
- `frontend` (React/Vite)
- `postgres`
- `mongo`
- `redis`
- `nats`
- `prometheus`
- `grafana`
- `postgres-exporter`
- `mongodb-exporter`
- `redis-exporter`
- `node-exporter`

Check containers:

```bash
docker compose ps
```

What to expect:
- Services should be `Up` (some may take a short warm-up period).

## 4) Runtime Smoke Checks

### Health endpoint

```bash
curl http://localhost:8000/health
```

What to expect:
- JSON response with dependency statuses (`redis`, `postgres`, `mongo`, `nats`).

### Prometheus metrics endpoint

```bash
curl http://localhost:8000/metrics
```

What to expect:
- Prometheus text exposition including app metrics like:
  - `http_requests_total`
  - `http_request_duration_seconds`
  - `signals_ingested_total`
  - `incident_state_transitions_total`
  - `rca_submissions_total`

### Generate sample load/events

```bash
python scripts/simulate_failures.py
python scripts/seed_data.py
```

What to expect:
- Signal/incident activity appears in backend logs and dashboard.
- Metrics start moving in Prometheus/Grafana panels.

## 5) Observability Validation

### Prometheus

Open:
- `http://localhost:9090`

Check:
- `Status` -> `Targets`

What to expect:
- `backend` target is `UP` (scraping `/metrics`).
- Exporter targets are `UP` (postgres, mongo, redis, node).
- NATS scrape target is `UP` on monitoring endpoint.

### Grafana

Open:
- `http://localhost:3000`
- Login: `admin / admin` (unless changed)

What to expect:
- Prometheus datasource auto-provisioned.
- IMS dashboard available from `monitoring/grafana/ims-observability-dashboard.json`.
- Panels populate after traffic generation.

## 6) Common Issues and Fixes

- No metrics on dashboard:
  - Confirm Prometheus target `backend:8000/metrics` is `UP`.
  - Generate events with `simulate_failures.py`.

- Backend health degraded:
  - Check container logs:
    ```bash
    docker compose logs -f backend
    ```

- Grafana dashboard empty:
  - Verify datasource points to `http://prometheus:9090`.
  - Confirm query metric names match exported names.

- Test path errors:
  - Use `backend/tests` and `backend/src` (repo was reorganized).

## 7) Shutdown

```bash
docker compose down
```

Remove volumes too (destructive for local DB data):

```bash
docker compose down -v
```

