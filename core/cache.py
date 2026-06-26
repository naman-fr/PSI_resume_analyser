import os
import json
import logging
from typing import Optional, Any
import redis

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.client = None
        self._memory_fallback = {}
        
        if self.redis_url:
            try:
                self.client = redis.Redis.from_url(self.redis_url, decode_responses=True)
                self.client.ping()
                logger.info("Successfully connected to Redis cache.")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis. Falling back to in-memory cache. Error: {e}")
                self.client = None
        else:
            logger.info("No REDIS_URL provided. Using open-source local memory fallback cache.")

    def get(self, key: str) -> Optional[Any]:
        try:
            if self.client:
                val = self.client.get(key)
                if val:
                    return json.loads(val)
            else:
                return self._memory_fallback.get(key)
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
        return None

    def set(self, key: str, value: Any, expire_seconds: int = 3600):
        try:
            val_str = json.dumps(value, default=str)
            if self.client:
                self.client.setex(key, expire_seconds, val_str)
            else:
                self._memory_fallback[key] = value
                # Note: memory fallback doesn't enforce expiry strictly in this basic implementation
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")

    def invalidate(self, key: str):
        try:
            if self.client:
                self.client.delete(key)
            else:
                self._memory_fallback.pop(key, None)
        except Exception as e:
            logger.error(f"Cache invalidate error for {key}: {e}")

cache = CacheManager()
