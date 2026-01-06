"""
Test Redis connection to AWS ElastiCache
"""

import asyncio
import redis.asyncio as redis
from dotenv import load_dotenv
import os

load_dotenv()


async def test_redis():
    try:
        # Connect to Redis
        print("🔗 Connecting to Redis...")
        print(f"   URL: {os.getenv('REDIS_URL')}")
        
        r = await redis.from_url(
            os.getenv('REDIS_URL'),
            encoding="utf-8",
            decode_responses=True
        )
        
        # Test ping
        pong = await r.ping()
        print(f"✅ Redis PING: {pong}")
        
        # Test set/get
        await r.set("test_key", "Hello from AgenticProject!")
        value = await r.get("test_key")
        print(f"✅ Redis GET: {value}")
        
        # Test expiry (TTL)
        await r.setex("temp_key", 60, "Expires in 60 seconds")
        ttl = await r.ttl("temp_key")
        print(f"✅ Redis TTL: {ttl} seconds")
        
        # Clean up
        await r.delete("test_key", "temp_key")
        print(f"✅ Cleanup successful")
        
        # Get info
        info = await r.info()
        print(f"\n📊 Redis Info:")
        print(f"   Version: {info.get('redis_version')}")
        print(f"   Connected clients: {info.get('connected_clients')}")
        print(f"   Used memory: {info.get('used_memory_human')}")
        print(f"   Uptime (days): {info.get('uptime_in_days')}")
        
        await r.close()
        print("\n✅ Redis connection test successful!")
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check if Redis is running")
        print("   2. Verify REDIS_URL in .env file")
        print("   3. Check security group allows port 6379")
        print("   4. Ensure VPC/network connectivity")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("  Redis Connection Test")
    print("=" * 60)
    print()
    
    asyncio.run(test_redis())
    
    print("\n" + "=" * 60)
