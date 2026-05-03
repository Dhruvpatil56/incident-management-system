# IMS Master Execution Plan & Specification

**Role:** You are an expert Principal Data/Backend Engineer.
**Task:** Build a mission-critical Incident Management System (IMS) to monitor a distributed stack, manage failure workflows, and handle massive concurrency.

## 1. Technical Stack Constraints

- **Backend:** Python (FastAPI) - completely async.
- **Message Broker / Ingestion:** NATS (to buffer 10k signals/sec).
- **Data Lake (Audit Log):** MongoDB (Schema-less storage for high-volume raw signal payloads).
- **Source of Truth (RDBMS):** PostgreSQL (Strict ACID transactions for work item states and RCA data).
- **Hot-Path Cache & Debouncer:** Redis (For real-time UI state and signal deduplication).
- **Frontend:** React (Vite + TypeScript + Tailwind) for the interactive dashboard.

## 2. Core Functional Requirements

### A. The Ingestion Engine (High-Throughput)

- **Backpressure:** The API must use an in-memory Token Bucket rate-limiter to prevent cascading failures.
- **Buffering:** Signals must be published to NATS immediately so the API doesn't wait on slow database writes.
- **Debouncing:** If 100 identical signals (same Component ID) arrive within 10 seconds, map all 100 raw signals in MongoDB to **one** single Incident Work Item in PostgreSQL using Redis to track the time window.

### B. The Workflow Engine (Strict Design Patterns)

- **Alerting:** Implement a "Strategy Pattern" for alerts (e.g., P0 triggers PagerDuty/Slack, P2 triggers Email).
- **State Management:** Implement an Object-Oriented "State Design Pattern" for the incident lifecycle (`OPEN` -> `INVESTIGATING` -> `RESOLVED` -> `CLOSED`).
- **RCA Guard:** The backend must strictly reject transitions to `CLOSED` unless a complete RCA (Root Cause Analysis) payload is attached.
- **Automated MTTR:** Automatically calculate Mean Time To Repair upon RCA submission.

### C. The Frontend Dashboard

- **Live Feed:** Polling or WebSockets to show active incidents sorted by severity.
- **Incident Detail:** View current status and a table of the raw linked signals pulled from MongoDB.
- **RCA Form:** A structured form requiring Start/End datetimes, a Root Cause Dropdown, and text areas for Fix Applied and Prevention Steps.

### D. Observability & Resilience

- **Metrics:** Expose a `/health` route and log system throughput (Signals/sec) every 5 seconds.
- **Retries:** Wrap external DB calls in exponential backoff retry logic (using `tenacity`) to handle transient database blips.
