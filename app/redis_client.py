import redis.asyncio as redis
from app.config import settings

redis_client: redis.Redis | None = None


async def init_redis() -> None:
    global redis_client
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def close_redis() -> None:
    if redis_client:
        await redis_client.aclose()


def get_redis() -> redis.Redis:
    assert redis_client is not None, "Redis não inicializado"
    return redis_client