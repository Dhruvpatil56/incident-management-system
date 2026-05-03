# Incident Pipeline - Command Reference

## Setup

```bash
# Install project + test deps
pip install -e ".[test]"

# (optional) Install with uv for speed
uv pip install -e ".[test]"
```

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=src/incident_pipeline -v --cov-report=term-missing

# Watch mode (auto-re-run on changes)
pip install pytest-watch
pytest-watch tests/

# Specific file
python -m pytest tests/test_rca_policy.py -v
```

## Running the Pipeline Manually

```bash
# Interactive Python session
python -c "
from incident_pipeline.pipeline import IncidentPipeline
from incident_pipeline.debounce import Debouncer
from incident_pipeline.rca import RcaPolicy
from incident_pipeline.cache import Cache, create_redis_client
from incident_pipeline.db.store import InMemoryStore
from incident_pipeline.models import Incident, RcaCategory

redis = create_redis_client()
p = IncidentPipeline(
    debouncer=Debouncer(redis),
    rca_policy=RcaPolicy(),
    cache=Cache(redis),
    store_fn=InMemoryStore().create,
)

incident = Incident(
    title='Test',
    description='Something broke',
    source='manual',
    root_cause='Deploy v2.3.1 introduced regression in payment handler',
    rca_category=RcaCategory.code_deploy,
    rca_description='Rolled back, added null check, redeployed',
)
print(p.process(incident))
"
```

## Docker

```bash
# Build
docker build -t incident-pipeline .

# Run tests inside container
docker run --rm incident-pipeline

# Run with Redis
docker network create inc-net
docker run -d --name redis --network inc-net redis:7-alpine
docker run --rm --network inc-net -e INCIDENT_REDIS_URL=redis://redis:6379/0 incident-pipeline python -c "
from incident_pipeline.debounce import Debouncer
import redis
r = redis.Redis(host='redis')
d = Debouncer(r)
print('Redis connected:', d.check.__doc__)
"

# Clean up
docker rm -f redis
docker network rm inc-net
```

## Environment Variables

```bash
# All configurable via env with INCIDENT_ prefix:
set INCIDENT_REDIS_URL=redis://localhost:6379/0
set INCIDENT_DATABASE_URL=postgresql://user:pass@localhost:5432/incidents
set INCIDENT_DEBOUNCE_WINDOW_SECONDS=30
set INCIDENT_CACHE_DEFAULT_TTL=300
set INCIDENT_CACHE_STAMPEDE_BETA=4.0
set INCIDENT_RCA_MIN_LENGTH=20
set INCIDENT_RCA_MAX_LENGTH=5000

# Or use .env file (supported via pydantic-settings)
```

## Lint & Type Check

```bash
pip install ruff mypy
ruff check src/
mypy src/
```

## SQL Migration

```bash
# Apply migration
psql -h localhost -U postgres -d incidents -f src/incident_pipeline/db/migration.py
# (Extract SQL first: python -c "from incident_pipeline.db.migration import MIGRATION_SQL; print(MIGRATION_SQL)" > migrate.sql)

# Or via script
python -c "
from incident_pipeline.db.migration import MIGRATION_SQL
with open('migrate.sql', 'w') as f:
    f.write(MIGRATION_SQL)
print('Written to migrate.sql')
"
psql -h localhost -U postgres -d incidents -f migrate.sql
```