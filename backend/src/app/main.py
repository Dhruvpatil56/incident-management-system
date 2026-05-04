from __future__ import annotations
from contextlib import asynccontextmanager
from time import perf_counter
import psycopg2
try:
    import nats
except ModuleNotFoundError:
    nats = None
import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ModuleNotFoundError:
    AsyncIOMotorClient = None
from app.config import app_settings
from app.dependencies import bootstrap_defaults
from app.routes.health import router as health_router
from app.routes.incidents import router as incidents_router
from app.routes.signals import router as signals_router
from observability.prometheus import observe_http, router as metrics_router
from signals.consumer import SignalConsumer
from signals.store import SignalStore

class _NoopNats:
    is_connected = False
    async def publish(self, _subject: str, _payload: bytes) -> None:
        return None
    async def drain(self) -> None:
        return None
    async def subscribe(self, _subject: str, cb=None) -> None:
        return None

class _NoopMongo:
    class _Admin:
        async def command(self, _cmd: str):
            return {"ok": 1}
    admin = _Admin()
    def __getitem__(self, key):
        return self
    def close(self):
        return None

class _NoopRedis:
    def ping(self):
        return True
    def close(self):
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.redis = redis.Redis.from_url(app_settings.redis_url)
        app.state.redis.ping()
    except Exception:
        app.state.redis = _NoopRedis()
    try:
        if AsyncIOMotorClient is None:
            raise RuntimeError("motor unavailable")
        app.state.mongo = AsyncIOMotorClient(app_settings.mongo_url, serverSelectionTimeoutMS=500)
        await app.state.mongo.admin.command("ping")
    except Exception:
        app.state.mongo = _NoopMongo()
    try:
        if nats is None:
            raise RuntimeError("nats unavailable")
        app.state.nats = await nats.connect(app_settings.nats_url, connect_timeout=0.5)
    except Exception:
        app.state.nats = _NoopNats()

    app.state.db = psycopg2.connect(app_settings.database_url)
    bootstrap_defaults(app)

    # Wire MongoDB signal store
    app.state.mongo_signal_store = SignalStore(
        app.state.mongo["incidents"]["signals"]
    )

    # Start the NATS consumer using MongoDB signal store
    consumer = SignalConsumer(
        nats_client=app.state.nats,
        subject=app_settings.nats_subject,
        store=app.state.mongo_signal_store,
        pipeline=app.state.pipeline,
        redis_client=app.state.redis,
    )
    await consumer.start()
    app.state.consumer = consumer

    await app.state.throughput.start()
    yield
    await app.state.throughput.stop()
    app.state.db.close()
    app.state.mongo.close()
    await app.state.nats.drain()
    app.state.redis.close()

app = FastAPI(title="Incident Management API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def metrics_middleware(request, call_next):
    started = perf_counter()
    response = await call_next(request)
    observe_http(request, response.status_code, started)
    return response

app.include_router(health_router)
app.include_router(signals_router)
app.include_router(incidents_router)
app.include_router(metrics_router)