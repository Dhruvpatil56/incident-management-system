from __future__ import annotations

from fastapi import APIRouter, Request

from observability.health import check_mongo, check_nats, check_postgres, check_redis

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict:
    redis_ok = await check_redis(getattr(request.app.state, "redis", None))
    postgres_ok = await check_postgres(getattr(request.app.state, "db", None))
    mongo_ok = await check_mongo(getattr(request.app.state, "mongo", None))
    nats_ok = await check_nats(getattr(request.app.state, "nats", None))
    all_ok = redis_ok and postgres_ok and mongo_ok and nats_ok
    return {
        "status": "ok" if all_ok else "degraded",
        "redis": redis_ok,
        "postgres": postgres_ok,
        "mongo": mongo_ok,
        "nats": nats_ok,
    }
