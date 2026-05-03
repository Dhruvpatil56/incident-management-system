import pytest
from httpx import ASGITransport, AsyncClient

import app.main as app_main
from app.main import app
from incident_pipeline.models import RcaCategory


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._one = None
        self._all = []

    def execute(self, query, params=None):
        q = " ".join(query.strip().split()).lower()
        if q.startswith("select 1"):
            self._one = (1,)
            return
        if "insert into incidents" in q:
            (
                incident_id,
                title,
                description,
                source,
                root_cause,
                rca_category,
                rca_description,
                rca_verified_by,
                state,
                severity,
                component,
                first_signal_at,
                rca_submitted_at,
                mttr_seconds,
                incident_hash,
                metadata,
            ) = params
            row = (
                incident_id,
                title,
                description,
                source,
                root_cause,
                rca_category,
                rca_description,
                rca_verified_by,
                state,
                severity,
                component,
                first_signal_at,
                rca_submitted_at,
                mttr_seconds,
                incident_hash,
                {},
                self.conn.now,
                self.conn.now,
            )
            self.conn.rows[incident_id] = row
            self._one = row
            return
        if "from incidents where id =" in q and "for update" not in q:
            incident_id = params[0]
            self._one = self.conn.rows.get(incident_id)
            return
        if "from incidents" in q and "order by created_at desc" in q:
            self._all = list(self.conn.rows.values())
            return
        self._one = None

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all

    def close(self):
        return None


class _FakeConn:
    def __init__(self):
        from datetime import datetime

        self.now = datetime.utcnow()
        self.rows = {}

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


@pytest.fixture(autouse=True)
def _mock_infra(monkeypatch):
    import fakeredis

    monkeypatch.setattr(app_main.psycopg2, "connect", lambda *_args, **_kwargs: _FakeConn())
    monkeypatch.setattr(app_main.redis.Redis, "from_url", lambda *_args, **_kwargs: fakeredis.FakeRedis())


@pytest.mark.asyncio
async def test_health_route_exists():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_incident():
    payload = {
        "title": "API errors",
        "description": "Spike in 500s",
        "source": "monitor",
        "root_cause": "Deploy caused issue in auth middleware",
        "rca_category": RcaCategory.code_deploy.value,
        "rca_description": "Rollback and patch applied",
    }
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/incidents", json=payload)
    assert response.status_code == 200
