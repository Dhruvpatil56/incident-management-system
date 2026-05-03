from __future__ import annotations


async def check_redis(redis_client) -> bool:
    try:
        return bool(redis_client.ping())
    except Exception:
        return False


async def check_postgres(db_conn) -> bool:
    try:
        cursor = db_conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        return True
    except Exception:
        return False


async def check_mongo(mongo_client) -> bool:
    try:
        await mongo_client.admin.command("ping")
        return True
    except Exception:
        return False


async def check_nats(nats_client) -> bool:
    try:
        return bool(getattr(nats_client, "is_connected", False))
    except Exception:
        return False
