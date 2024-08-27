import aioredis
import os

redis = None
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost')
async def connect_to_redis():
    global redis
    redis = await aioredis.create_redis_pool(REDIS_URL, encoding="utf-8")
    print("connected to redis")

async def close_redis_connection():
    if redis:
        redis.close()
        await redis.wait_closed()

def get_redis_database():
    return redis