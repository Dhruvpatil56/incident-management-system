# Incident Management System: Build Order and Execution Flow

This document defines the actual creation order of the IMS, the goal of each step, and the stack used to deliver that step.

## Stack Summary

- Backend API: FastAPI (Python)
- Async Ingestion Buffer: NATS
- NoSQL Audit Log: MongoDB
- Relational Source of Truth: PostgreSQL
- Cache + Debounce + Hot Path: Redis
- Frontend: React + Vite + TypeScript
- Infra Orchestration: Docker Compose

## Phase 1: Foundation and Infrastructure Boot

Goal:
- Stand up all core services and create a stable local environment for development and testing.

What was created:
- Multi-service runtime with `postgres`, `mongo`, `redis`, `nats`, `backend`, and `frontend`.
- Service-to-service connectivity through Docker internal DNS.

Why this first:
- Every later feature (ingestion, storage, workflow) depends on reliable infrastructure.

Primary files:
- `compose.yaml`
- `backend/Dockerfile`
- `frontend/Dockerfile`

## Phase 2: Ingestion and Backpressure Guardrails

Goal:
- Accept high traffic safely and prevent API collapse during burst conditions.

What was created:
- `POST /api/v1/signals` ingestion endpoint.
- In-memory Token Bucket limiter for admission control.
- Async publish to NATS to decouple API latency from downstream writes.

Why this second:
- High-throughput safety must exist before adding complex processing logic.

Primary files:
- `backend/src/app/routes/signals.py`
- `backend/src/ingestion/rate_limiter.py`
- `backend/src/ingestion/producer.py`

## Phase 3: Signal Processing, Debounce, and Data Routing

Goal:
- Convert raw signals into resilient incident creation behavior with deduplication.

What was created:
- NATS consumer pipeline for signal handling.
- Redis-backed debouncing to prevent duplicate incident creation in short windows.
- Raw signal persistence in MongoDB for auditability.

Why this third:
- We need controlled, deterministic processing before workflow/state operations.

Primary files:
- `backend/src/signals/consumer.py`
- `backend/src/signals/store.py`
- `backend/src/incident_pipeline/debounce/deduper.py`

## Phase 4: Incident Source of Truth and ACID Operations

Goal:
- Persist incident lifecycle data with transactional correctness.

What was created:
- PostgreSQL-backed incident store.
- Transactional create/update paths with commit/rollback behavior.
- Row-locking (`FOR UPDATE`) for safe concurrent state/RCA updates.

Why this fourth:
- Durable, consistent incident records are required before enforcing strict workflow rules.

Primary files:
- `backend/src/incident_pipeline/db/store.py`
- `backend/src/app/main.py`
- `backend/src/app/dependencies.py`

## Phase 5: Workflow Engine and Guarded State Machine

Goal:
- Enforce incident lifecycle transitions and prevent invalid closure.

What was created:
- Object-oriented State Design Pattern (`OpenState`, `InvestigatingState`, `ResolvedState`, `ClosedState`).
- Transition guard that rejects close when RCA is incomplete.
- API transition path wired to state classes and errors.

Why this fifth:
- State correctness depends on ACID-backed persistence and stable incident identity.

Primary files:
- `backend/src/workflow/state_machine.py`
- `backend/src/workflow/rca_guard.py`
- `backend/src/app/routes/incidents.py`

## Phase 6: RCA Submission and MTTR Computation

Goal:
- Capture complete remediation context and calculate repair duration automatically.

What was created:
- Structured RCA payload handling (start/end, category, fix, prevention).
- MTTR computation from incident start/end timestamps.
- Transactional RCA update path in Postgres.

Why this sixth:
- RCA quality and MTTR depend on completed workflow + persisted incident records.

Primary files:
- `backend/src/app/routes/incidents.py`
- `backend/src/incident_pipeline/db/store.py`

## Phase 7: Alerting and Observability

Goal:
- Improve operational response and runtime visibility.

What was created:
- Strategy Pattern alert routing by severity.
- `/health` endpoint across dependencies.
- Throughput counter loop logging `Signals/sec` every 5 seconds.

Why this seventh:
- Once the critical data path is stable, visibility and on-call response become actionable.

Primary files:
- `backend/src/alerting/router.py`
- `backend/src/app/routes/health.py`
- `backend/src/observability/metrics.py`

## Phase 8: Frontend Experience and Typed RCA UX

Goal:
- Provide actionable operator UI and enforce structured input quality at the edge.

What was created:
- Severity-sorted incident dashboard with periodic refresh.
- Incident detail screen with linked raw signals.
- Typed RCA form with datetime pickers, dropdown category, and dedicated textareas.

Why this eighth:
- UI is most effective after backend contracts, validation rules, and workflows are stable.

Primary files:
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/IncidentDetail.tsx`
- `frontend/src/components/RcaForm.tsx`
- `frontend/src/types/incident.ts`

## Final Outcome

The IMS now follows a creation order optimized for reliability:
1. Stand up infra.
2. Protect ingestion.
3. Process + dedupe signals.
4. Persist incidents with ACID guarantees.
5. Enforce state-machine workflow.
6. Capture RCA and compute MTTR.
7. Add alerts and observability.
8. Deliver operator-facing UI with typed workflows.

