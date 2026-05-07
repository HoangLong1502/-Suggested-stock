import json
from typing import AsyncGenerator

import redis.asyncio as redis

from app.core.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def publish(channel: str, payload: dict) -> None:
    await redis_client.publish(channel, json.dumps(payload))


async def subscribe(channel: str) -> AsyncGenerator[dict, None]:
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message and message.get('type') == 'message':
                data = message.get('data')
                try:
                    yield json.loads(data)
                except Exception:
                    continue
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
