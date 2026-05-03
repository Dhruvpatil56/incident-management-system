from __future__ import annotations

import redis

from incident_pipeline.config import settings


def create_redis_pool() -> redis.ConnectionPool:
    """Create a shared Redis connection pool.

    Connection pooling prevents creating a new TCP connection per request
    and provides health checks so broken connections are pruned.
    """
    return redis.ConnectionPool.from_url(
        settings.redis_url,
        max_connections=settings.redis_max_connections,
        socket_connect_timeout=settings.redis_socket_timeout,
        socket_timeout=settings.redis_socket_timeout,
        retry_on_timeout=True,
        health_check_interval=settings.redis_health_check_interval,
    )


def create_redis_client(pool: redis.ConnectionPool | None = None) -> redis.Redis:
    if pool is None:
        pool = create_redis_pool()
    return redis.Redis(connection_pool=pool)