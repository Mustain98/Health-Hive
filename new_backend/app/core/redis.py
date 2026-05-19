import os
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_PASS = os.getenv("REDIS_PASS")

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    password=REDIS_PASS,
    decode_responses=True
)

def get_redis() -> redis.Redis:
    return redis_client