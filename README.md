# 🚀 Incident Management System (IMS)

> A mission-critical, distributed system engineered for high-throughput failure ingestion, strict incident lifecycle enforcement, and real-time observability.

---

## 🏗️ Architecture & Tech Stack

![Incident Management System Architecture](./Incident%20management%20system%20architecture%20diagram.png)

The system is built as a polyglot, event-driven ecosystem with a strict separation of responsibilities:

- **[FastAPI]** - Async backend driving the ingestion pipeline, state machine workflows, and strict RCA validation.
- **[NATS]** - High-performance message broker acting as an asynchronous shock absorber between ingestion and processing.
- **[PostgreSQL]** - The ACID-compliant Source of Truth for incident records, workflow states, and MTTR calculations.
- **[MongoDB]** - Schema-flexible Data Lake for high-volume, raw signal audit storage.
- **[Redis]** - In-memory engine for sub-millisecond debouncing and hot-path burst controls.
- **[Prometheus & Grafana]** - Full-stack telemetry, metrics collection, and live visualization.

---

## ⚡ Quick Start

### Prerequisites

- Docker Engine
- Docker Compose v2 (`docker compose`)

### Booting the Stack

1. Open a terminal in the repository root.
2. Build and spin up the entire distributed ecosystem:

   docker compose up -d --build

3. Verify all services are healthy:

   docker compose ps

4. _(Optional)_ Stream the logs to watch the system initialize:

   docker compose logs -f

5. Teardown the stack when finished:

   docker compose down

### 🌐 Service Matrix & Exposed Ports

| Service                             |  Port   | Local Address         |
| :---------------------------------- | :-----: | :-------------------- |
| **Frontend Dashboard** (React/Vite) | `5173`  | http://localhost:5173 |
| **Backend API** (FastAPI)           | `8000`  | http://localhost:8000 |
| **Grafana** (Metrics UI)            | `3000`  | http://localhost:3000 |
| **Prometheus**                      | `9090`  | http://localhost:9090 |
| **PostgreSQL**                      | `5432`  | `localhost:5432`      |
| **MongoDB**                         | `27017` | `localhost:27017`     |
| **Redis**                           | `6379`  | `localhost:6379`      |
| **NATS Broker**                     | `4222`  | `localhost:4222`      |
| **NATS Monitoring**                 | `8222`  | http://localhost:8222 |

_(Note: Exporters for Postgres `9187`, Mongo `9216`, Redis `9121`, and Node `9100` are also running internally for Prometheus scraping)._

---

## 🛡️ Backpressure & Resilience Strategy

How does the system survive bursts of **10,000 signals/sec** without collapsing? We utilize a layered, fail-safe defense strategy:

### 1. Edge Protection (Admission Control)

The ingestion edge is protected by an **in-memory Token Bucket**. Each incoming request to the signal ingestion endpoint consumes tokens from a bounded bucket. Once depleted, excess requests are rejected immediately with a `429 Too Many Requests` response. This prevents unbounded memory queueing inside the API process and preserves responsiveness under bursty client behavior. Additionally, in-flight processing is bounded with a semaphore; if saturated, it returns `503 Service Unavailable`, creating a secondary pressure-release valve.

### 2. Asynchronous Buffering (The Shock Absorber)

After passing admission control, accepted signals are **not** written synchronously to a database. Instead, they are published directly to **NATS**. This message broker acts as an asynchronous shock absorber, decoupling the blazing-fast API ingestion path from the slower persistence path. Consumers drain the NATS broker at a controlled rate, allowing compute and storage layers to recover naturally from pressure spikes while keeping API ingestion latency perfectly flat.

### 3. Persistence Stability (Deduplication & Retries)

At the persistence layer, resilience is reinforced through intelligent data routing:

- **Atomic Debouncing:** Redis-backed debounce mechanisms intercept duplicate failure signals (failure storms) and drop them before they can amplify database write pressure.
- **Exponential Backoff:** Database operations are wrapped in retry/backoff policies. Instead of failing fast across the pipeline during a database blip, the system absorbs transient faults and self-heals.

**The Result:** Reject early when unsafe, buffer asynchronously when acceptable, and stabilize downstream writes through deduplication and bounded retries.
