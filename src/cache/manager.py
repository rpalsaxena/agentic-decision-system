"""
Redis cache manager for rate limiting and idempotency.

Provides high-performance operations for:
- Rate limiting (using sliding window)
- Idempotency checking (TTL-based)
- General caching
"""

import redis.asyncio as redis
import os
from typing import Optional
from datetime import timedelta


class CacheManager:
    """
    Redis-backed cache for hot-path operations.
    
    Features:
    - Rate limiting with atomic operations
    - Idempotency checks with TTL
    - Connection pooling
    """
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
    
    async def connect(self, redis_url: Optional[str] = None):
        """
        Connect to Redis.
        
        Args:
            redis_url: Redis connection string. Falls back to REDIS_URL env var.
        """
        url = redis_url or os.getenv('REDIS_URL')
        if not url:
            raise ValueError("REDIS_URL not set")
        
        self.client = await redis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10
        )
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
    
    # ========================================
    # RATE LIMITING
    # ========================================
    
    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 3600
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded using sliding window.
        
        Args:
            key: Unique identifier (e.g., "actions:user:123")
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds (default 1 hour)
            
        Returns:
            Tuple of (allowed: bool, current_count: int)
        """
        rate_key = f"rate:{key}"
        
        # Increment counter
        count = await self.client.incr(rate_key)
        
        # Set expiry on first request
        if count == 1:
            await self.client.expire(rate_key, window_seconds)
        
        # Check if limit exceeded
        allowed = count <= max_requests
        
        return allowed, count
    
    async def get_rate_limit_status(self, key: str) -> dict:
        """
        Get current rate limit status for a key.
        
        Returns:
            Dict with current count and TTL
        """
        rate_key = f"rate:{key}"
        
        count = await self.client.get(rate_key)
        ttl = await self.client.ttl(rate_key)
        
        return {
            "count": int(count) if count else 0,
            "ttl": ttl if ttl > 0 else 0
        }
    
    async def reset_rate_limit(self, key: str):
        """Reset rate limit counter for a key"""
        rate_key = f"rate:{key}"
        await self.client.delete(rate_key)
    
    # ========================================
    # IDEMPOTENCY
    # ========================================
    
    async def check_idempotency(
        self,
        event_hash: str,
        ttl_seconds: int = 3600
    ) -> bool:
        """
        Check if event was already processed (idempotency).
        
        Args:
            event_hash: Unique hash of the event
            ttl_seconds: How long to remember (default 1 hour)
            
        Returns:
            True if already processed, False if new
        """
        idem_key = f"idem:{event_hash}"
        
        # Check if key exists
        exists = await self.client.exists(idem_key)
        
        if exists:
            return True  # Already processed
        
        # Mark as processed
        await self.client.setex(idem_key, ttl_seconds, "1")
        
        return False  # New event
    
    async def mark_processed(
        self,
        event_hash: str,
        ttl_seconds: int = 3600
    ):
        """
        Mark an event as processed for idempotency.
        
        Args:
            event_hash: Unique hash of the event
            ttl_seconds: How long to remember
        """
        idem_key = f"idem:{event_hash}"
        await self.client.setex(idem_key, ttl_seconds, "1")
    
    # ========================================
    # GENERAL CACHING
    # ========================================
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        return await self.client.get(key)
    
    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: Optional[int] = None
    ):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to store
            ttl_seconds: Optional TTL
        """
        if ttl_seconds:
            await self.client.setex(key, ttl_seconds, value)
        else:
            await self.client.set(key, value)
    
    async def delete(self, key: str):
        """Delete key from cache"""
        await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return await self.client.exists(key) > 0
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a counter.
        
        Returns:
            New value after increment
        """
        return await self.client.incrby(key, amount)
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """
        Decrement a counter.
        
        Returns:
            New value after decrement
        """
        return await self.client.decrby(key, amount)
    
    async def get_info(self) -> dict:
        """Get Redis server info"""
        info = await self.client.info()
        return {
            "version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
            "uptime_days": info.get("uptime_in_days")
        }


# Global cache instance
cache = CacheManager()
