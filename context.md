# Incident Management System (IMS) – Context

## Objective

Build a resilient Incident Management System (IMS) that ingests high-volume signals from a distributed system, processes them intelligently, and manages the full lifecycle of incidents (Work Items) from detection to closure with mandatory Root Cause Analysis (RCA).

This system simulates real-world SRE/DevOps incident handling in production environments.

---

## System Scope

The system monitors a distributed stack including:

- APIs
- MCP Hosts
- Distributed Caches
- Async Queues
- RDBMS
- NoSQL Databases

It must:

- Handle high-throughput signal ingestion (up to 10,000 signals/sec)
- Group related signals into incidents (debouncing)
- Store raw and structured data separately
- Provide alerting and workflow management
- Offer a real-time dashboard with RCA enforcement

---

## Core Architecture

### 1. Ingestion Layer (Producer)

- Accept high-throughput signals via API or messaging system
- Handle burst traffic without crashing (backpressure required)
- Implement debouncing:
  - Multiple signals for same Component ID within 10 seconds → one Work Item
  - All signals linked in NoSQL

---

### 2. Storage & Distribution Layer

#### Raw Signal Store (Data Lake)

- Stores all incoming signals as an immutable audit log
- Should support querying for debugging and analysis

#### Source of Truth (Work Items + RCA)

- Stores structured incidents and RCA records
- Requires transactional consistency for state transitions

#### Cache Layer (Hot Path)

- Maintains real-time dashboard state
- Reduces load on primary database

#### Aggregation Store

- Supports time-series metrics like MTTR and trends

---

### 3. Workflow Engine

#### State Management (State Pattern)

Incident lifecycle:
OPEN → INVESTIGATING → RESOLVED → CLOSED

- Enforce valid transitions
- Prevent invalid state changes

#### Alerting Strategy (Strategy Pattern)

- Different components map to different severities:
  - P0 → Critical (e.g., RDBMS failure)
  - P2 → Non-critical (e.g., cache issue)

- Alerting logic must be pluggable and extensible

---

## Functional Requirements

### Backend

- Fully asynchronous processing system
- Mandatory RCA:
  - Cannot transition Work Item to CLOSED without complete RCA

- MTTR Calculation:
  - Start time = first signal timestamp
  - End time = RCA submission timestamp

---

### Frontend Dashboard

Must include:

#### Live Feed

- Display active incidents sorted by severity

#### Incident Detail View

- Show raw signals (from NoSQL)
- Display current state

#### RCA Form

- Incident Start Time
- Incident End Time
- Root Cause Category
- Fix Applied
- Prevention Steps

---

## Non-Functional Requirements

### Concurrency

- Use modern concurrency primitives
- Avoid race conditions

### Rate Limiting

- Protect ingestion API from overload

### Observability

- Provide `/health` endpoint
- Log throughput (signals/sec every 5 seconds)

### Resilience

- Implement retry logic for database operations
- Handle backpressure gracefully

---

## Evaluation Criteria

- Concurrency & Scaling: Handle high-volume signals safely
- Data Handling: Proper separation of concerns
- Low-Level Design: Clean architecture and design patterns
- UI/UX & Integration: Functional dashboard
- Resilience & Testing: Retry logic and validations
- Documentation: Clear README and supporting docs
- Tech Stack Choices: Well-justified architecture

---

## Repository Structure

/backend
/frontend
README.md
context.md
docker-compose.yml
sample-data/

---

## Additional Requirements

- Provide architecture diagram
- Include setup instructions using Docker Compose
- Explain backpressure handling
- Provide sample data or scripts to simulate failures
- Include all prompts/specs used during development

---

## Design Goals

- Simulate real-world incident management workflows
- Handle high-throughput distributed systems
- Apply design patterns (State, Strategy)
- Ensure observability, resilience, and scalability

---

## Key Challenges

- Processing 10k signals/sec without data loss
- Implementing efficient debouncing logic
- Maintaining consistency across distributed components
- Avoiding database bottlenecks using caching
- Enforcing strict RCA validation rules

---

## Suggested Tech Stack (Flexible)

- Backend: Go / Java / Node.js
- Messaging: Kafka / NATS / RabbitMQ
- Cache: Redis
- Database:
  - PostgreSQL (source of truth)
  - MongoDB / DynamoDB (signals)

- Frontend: React
- Observability: Prometheus + Grafana

---

## Reference

Derived from assignment specification:
