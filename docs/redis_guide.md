# Redis Deep Dive: For AI Systems Engineers

**Context**: Why Redis matters for agentic AI systems  
**Audience**: Engineers new to Redis, preparing for Staff+ roles

---

# Section 1: The Essentials (5-Minute Read)

## What Redis Actually Is

**Redis = Remote Dictionary Server**

Think of it as a **HashMap that lives on a server** instead of in your Python process.

```python
# Python dict (in-memory, single process)
cache = {"user:123": "active"}

# Redis (network-accessible, shared across processes)
await redis.set("user:123", "active")
```

## Why It Exists

| Problem | Solution Without Redis | Solution With Redis |
|---------|------------------------|---------------------|
| Rate limiting | Dict in memory — lost on restart | Persists, shared across instances |
| Session storage | Disk or DB — slow | Sub-millisecond |
| Caching | Memory — can't scale horizontally | Shared cache across all servers |
| Pub/Sub | Build your own message queue | Built-in |

## The One Thing to Remember

> **Redis is for data that needs to be fast AND shared across processes.**

If it's just fast → use Python dict  
If it's just shared → use PostgreSQL  
If it's **fast + shared** → use Redis

---

## Core Operations You'll Use (80% of real usage)

### 1. SET and GET (Key-Value)
```python
# Store a value
await redis.set("event:abc123:processed", "1")

# Get it back
result = await redis.get("event:abc123:processed")  # "1" or None
```

### 2. SETEX (Set with Expiration) — Most Important for Us
```python
# Set with 1-hour TTL (Time To Live)
await redis.setex("idem:event_hash_xyz", 3600, "1")

# After 3600 seconds, key automatically deleted
```

This is **idempotency** in one line. No cleanup jobs needed.

### 3. INCR (Atomic Increment) — Rate Limiting
```python
# Atomic increment — no race conditions
count = await redis.incr("rate:user:123:hour:2024011510")

# First call: returns 1
# Second call: returns 2
# Tenth call: returns 10 → block if limit is 10
```

### 4. EXISTS (Check If Key Exists)
```python
if await redis.exists("idem:event_hash_xyz"):
    return "Already processed"
```

---

## How We Use Redis in This Project

| Use Case | Redis Pattern | Why Not PostgreSQL |
|----------|---------------|-------------------|
| **Idempotency** | `SETEX idem:{hash} 3600 1` | Checking every event needs <1ms |
| **Rate Limiting** | `INCR rate:{source}:{hour}` | Atomic increment, auto-expiry |
| **Distributed Lock** | `SET lock:{resource} NX EX 30` | Need fast acquire/release |

---

## Mental Model

```
┌─────────────────────────────────────────────────────────┐
│                     Your Application                     │
├─────────────────────────────────────────────────────────┤
│  Hot Path (every request)    │  Cold Path (occasional)  │
│  ──────────────────────────  │  ─────────────────────── │
│  • Rate limit check          │  • Store event           │
│  • Idempotency check         │  • Store decision        │
│  • Session lookup            │  • Query audit logs      │
│           ↓                  │           ↓              │
│         REDIS                │       POSTGRESQL         │
│        (<1ms)                │        (5-50ms)          │
└─────────────────────────────────────────────────────────┘
```

---

# Section 2: Deep Dive (For Further Study)

## Data Types in Redis

Redis isn't just key-value. It has **5 core data types**:

### 1. Strings (Most Common)
```python
# Simple values
await redis.set("config:threshold", "0.75")
value = await redis.get("config:threshold")  # "0.75" (always string)

# Counter
await redis.incr("metrics:events_processed")
await redis.incrby("metrics:events_processed", 10)
```

### 2. Hashes (Like Nested Dicts)
```python
# Store object fields
await redis.hset("user:123", mapping={
    "name": "Alice",
    "role": "admin",
    "last_login": "2024-01-15T10:30:00Z"
})

# Get single field
name = await redis.hget("user:123", "name")  # "Alice"

# Get all fields
user = await redis.hgetall("user:123")  # {"name": "Alice", "role": "admin", ...}
```

**When to use**: When you need to update individual fields without fetching entire object.

### 3. Lists (Ordered, Duplicates Allowed)
```python
# Push to list
await redis.lpush("queue:events", json.dumps(event))

# Pop from other end (FIFO queue)
event_json = await redis.rpop("queue:events")

# Get range
recent = await redis.lrange("recent:events", 0, 9)  # Last 10
```

**When to use**: Job queues, activity feeds, recent items.

### 4. Sets (Unique, Unordered)
```python
# Add to set
await redis.sadd("active:users", "user:123", "user:456")

# Check membership
is_active = await redis.sismember("active:users", "user:123")  # True/False

# Get all members
users = await redis.smembers("active:users")
```

**When to use**: Unique collections, tags, tracking unique visitors.

### 5. Sorted Sets (Unique with Score)
```python
# Add with score (e.g., timestamp)
await redis.zadd("leaderboard", {"user:123": 1500, "user:456": 1200})

# Get top 10
top_users = await redis.zrevrange("leaderboard", 0, 9, withscores=True)

# Get rank
rank = await redis.zrevrank("leaderboard", "user:123")  # 0 = first place
```

**When to use**: Leaderboards, rate limiting with sliding windows, priority queues.

---

## Persistence Options

Redis can persist data to disk:

| Mode | How It Works | Durability | Performance |
|------|--------------|------------|-------------|
| **None** | Memory only | Lost on restart | Fastest |
| **RDB** | Periodic snapshots | Lose up to X minutes | Fast |
| **AOF** | Log every write | Lose up to 1 second | Slower |
| **RDB + AOF** | Both | Best durability | Slowest |

### For Our Project
**None or RDB is fine.** Rate limit counters and idempotency keys can be lost on restart — worst case: a few duplicate actions. Not critical.

---

## Connection Pooling

Just like PostgreSQL, don't open a new connection per request:

```python
# BAD: New connection every time
async def check_rate_limit():
    redis = await aioredis.from_url("redis://localhost")  # 2-5ms overhead
    count = await redis.incr("rate:...")
    await redis.close()

# GOOD: Reuse connection pool
pool = await aioredis.from_url("redis://localhost", max_connections=10)

async def check_rate_limit():
    count = await pool.incr("rate:...")  # <1ms
```

---

## Key Naming Conventions

**Pattern**: `namespace:entity:id:attribute`

```
rate:source:monitoring:hour:2024011510
idem:event:abc123def456
lock:decision:event_id_789
cache:user:123:profile
```

### Why This Matters
1. **Avoid collisions** — `user:123` vs `event:123`
2. **Easy to debug** — Know what you're looking at
3. **Pattern matching** — `KEYS rate:*` finds all rate limit keys
4. **TTL management** — Different namespaces, different expiry policies

---

## Redis vs Memcached

| Aspect | Redis | Memcached |
|--------|-------|-----------|
| Data types | Strings, Hashes, Lists, Sets, Sorted Sets | Strings only |
| Persistence | Optional | None |
| Pub/Sub | Yes | No |
| Lua scripting | Yes | No |
| Clustering | Yes | Yes |
| Memory efficiency | Slightly less | Slightly more |

### When Memcached Wins
- Pure caching, no other features needed
- Maximum memory efficiency matters
- Very simple use case

### When Redis Wins
- Need data structures (our case)
- Need atomic operations (our case)
- Need TTL per key (our case)
- Need pub/sub or streams

**For AI systems: Redis is almost always the right choice.**

---

## AWS ElastiCache vs Upstash vs Self-Hosted

| Option | Pros | Cons | Cost |
|--------|------|------|------|
| **ElastiCache** | Managed, AWS-integrated | Fixed capacity, always running | ~$15/month minimum |
| **Upstash** | Serverless, scale to zero | Per-request pricing | $0.20/100K commands |
| **Self-hosted** | Full control | You manage everything | EC2 cost + time |

### Recommendation for This Project

**Upstash** — Matches our serverless Aurora choice:
- Pay only when you use it
- No server management
- Free tier: 10K commands/day
- Global edge (low latency)

```python
# Upstash connection
REDIS_URL = "redis://default:xxxxx@us1-xxxxx.upstash.io:6379"
```

---

## Common Pitfalls

### 1. Forgetting TTL
```python
# BAD: Keys accumulate forever
await redis.set("temp:data", value)

# GOOD: Always set TTL for temporary data
await redis.setex("temp:data", 3600, value)
```

### 2. Large Values
```python
# BAD: Storing MB of data
await redis.set("big:data", massive_json)  # Blocks other operations

# GOOD: Store in S3/DB, cache reference
await redis.set("big:data:ref", "s3://bucket/key")
```

### 3. Blocking Operations
```python
# BAD: KEYS in production (scans entire keyspace)
keys = await redis.keys("rate:*")  # O(n), blocks Redis

# GOOD: Use SCAN for iteration
async for key in redis.scan_iter("rate:*"):
    ...
```

### 4. No Expiry on Rate Limit Keys
```python
# BAD: Old rate limit keys never expire
await redis.incr(f"rate:{source}")

# GOOD: Key includes time bucket, expires with TTL
key = f"rate:{source}:hour:{current_hour}"
await redis.incr(key)
await redis.expire(key, 7200)  # Expire after 2 hours
```

---

# Section 3: Interview Q&A

## Fundamental Questions

### Q: What is Redis and when would you use it?
**A**: Redis is an in-memory data structure store. I use it when I need:
1. **Fast shared state** — Data accessed by multiple processes in <1ms
2. **Transient data** — Things like rate limits, sessions, caches that can be lost
3. **Atomic operations** — Counter increments without race conditions

In our agentic AI system, we use Redis for rate limiting (INCR) and idempotency checking (SETEX) because these happen on every event and need sub-millisecond latency.

---

### Q: Why Redis over PostgreSQL for rate limiting?
**A**: Three reasons:
1. **Latency** — Redis is ~0.1ms, PostgreSQL is ~5-50ms. Rate limiting happens on every request.
2. **Atomic increment** — `INCR` is lock-free. In PostgreSQL, you'd need `SELECT FOR UPDATE` or transactions.
3. **Auto-expiry** — TTL is built-in. No need for a cleanup job.

---

### Q: How do you implement rate limiting with Redis?
**A**: Using INCR with time-bucketed keys:
```python
hour_bucket = datetime.now().strftime("%Y%m%d%H")
key = f"rate:{source}:hour:{hour_bucket}"

count = await redis.incr(key)
if count == 1:
    await redis.expire(key, 7200)  # First increment sets TTL

if count > LIMIT:
    raise RateLimitExceeded()
```

The time bucket approach is simpler than sliding windows and sufficient for most cases.

---

### Q: How do you ensure idempotency with Redis?
**A**: SETEX with a deterministic hash:
```python
event_hash = sha256(json.dumps(event, sort_keys=True)).hexdigest()
key = f"idem:{event_hash}"

# NX = only set if not exists
was_set = await redis.set(key, "1", nx=True, ex=3600)
if not was_set:
    return "Already processed"
```

The `NX` flag makes the check-and-set atomic — no race conditions.

---

## Architecture Questions

### Q: How do you decide what goes in Redis vs PostgreSQL?
**A**: My mental model:

| Redis | PostgreSQL |
|-------|------------|
| Hot path (every request) | Cold path (occasional) |
| OK to lose on restart | Must survive restart |
| Simple lookups | Complex queries |
| Transient state | Source of truth |

Specifically:
- Rate limits → Redis (hot, transient)
- Event records → PostgreSQL (cold, permanent)
- Idempotency → Redis (hot, can rebuild from logs)
- Audit logs → PostgreSQL (cold, permanent)

---

### Q: What happens if Redis goes down?
**A**: Depends on the use case:
1. **Rate limiting** — Fail open (allow requests) or fail closed (block). We fail closed to prevent runaway AI actions.
2. **Idempotency** — Fail open (risk duplicates) or fail closed (reject). We fail closed for the same reason.
3. **Caching** — Fall back to database.

In code:
```python
try:
    is_duplicate = await redis.exists(key)
except RedisError:
    logger.error("Redis unavailable, blocking request")
    return "Service temporarily unavailable"
```

---

### Q: How do you handle Redis in a distributed system?
**A**: 
1. **Single node for small scale** — Up to ~100K ops/second
2. **Redis Cluster for scale** — Automatic sharding by key hash
3. **Replicas for read scale** — Primary for writes, replicas for reads

For our project, single node (ElastiCache or Upstash) is plenty. We're doing maybe 100 ops/second max.

---

## Scenario Questions

### Q: Your rate limiter is allowing 12 requests when the limit is 10. What's wrong?
**A**: Possible causes:
1. **Race condition** — Check and increment not atomic. Solution: use `INCR` first, then check.
2. **Multiple key buckets** — Key includes hour but events span bucket boundary.
3. **TTL not set** — Old keys from previous period still incrementing.

Debug approach:
```python
# Check the actual key
current_count = await redis.get(rate_key)
ttl = await redis.ttl(rate_key)
print(f"Key: {rate_key}, Count: {current_count}, TTL: {ttl}")
```

---

### Q: How would you implement a sliding window rate limiter?
**A**: Two approaches:

**1. Sorted Set (precise)**:
```python
now = time.time()
window_start = now - 3600  # 1 hour ago

# Add current request
await redis.zadd(key, {str(uuid4()): now})

# Remove old entries
await redis.zremrangebyscore(key, 0, window_start)

# Count
count = await redis.zcard(key)
```

**2. Multiple fixed windows (approximate but faster)**:
```python
# Count current and previous window, weighted by time elapsed
current_window = await redis.get(f"rate:{current_minute}")
previous_window = await redis.get(f"rate:{previous_minute}")
elapsed_ratio = seconds_into_current_minute / 60
weighted_count = int(previous_window) * (1 - elapsed_ratio) + int(current_window)
```

For our use case, fixed windows are fine.

---

### Q: You need to cache LLM responses. How would you structure the Redis key?
**A**: I'd hash the prompt (or a normalized version):
```python
def cache_key(prompt: str, model: str, temperature: float) -> str:
    normalized = f"{model}:{temperature}:{prompt.strip().lower()}"
    return f"llm_cache:{sha256(normalized).hexdigest()[:16]}"

# Check cache
cached = await redis.get(cache_key(prompt, model, temp))
if cached:
    return json.loads(cached)

# Call LLM, cache result
result = await call_llm(prompt)
await redis.setex(cache_key(...), 3600, json.dumps(result))
```

Important: Temperature > 0 means responses vary, so caching may not make sense.

---

## Quick Fire

### Q: SETEX vs SET with EX?
**A**: Same thing. `SETEX key ttl value` = `SET key value EX ttl`. SETEX is older syntax.

### Q: What does NX mean?
**A**: "Not eXists" — only set if key doesn't exist. Used for locks and idempotency.

### Q: What's the max key size?
**A**: 512 MB, but keep keys short (< 1 KB). Use namespace:entity:id pattern.

### Q: What's the max value size?
**A**: 512 MB, but avoid large values. They block other operations.

### Q: How do you debug Redis?
**A**: 
- `redis-cli MONITOR` — Watch all commands in real-time
- `redis-cli INFO` — Server stats
- `redis-cli SLOWLOG GET 10` — Find slow commands

---

## The One-Line Summary

> "Redis is where you put data that needs to be fast and shared, but can be lost without catastrophic consequences."

For agentic AI: **Rate limiting, idempotency, and caching are Redis. Events, decisions, and audit logs are PostgreSQL.**

---

# Section 4: Design Decisions & Alternatives Analysis

## Why Redis? The Complete Rationale

This section documents our architectural decision-making process for choosing Redis in this agentic AI system. It covers alternatives considered, trade-offs analyzed, and when simpler solutions might work just as well.

---

## The Core Question: Do We Really Need Redis?

**Short answer**: For production AI systems at scale, yes. For prototypes or low-traffic scenarios, maybe not.

**Key insight**: The decision hinges on **throughput requirements** and **performance criticality**. Here's the framework:

### When Redis is Essential
- **High throughput** (>100 events/second)
- **Multi-process architecture** (multiple Lambda functions, ECS tasks, or servers)
- **Critical latency requirements** (<5ms for hot-path operations)
- **Concurrent access patterns** (multiple agents accessing shared state)

### When Simpler Solutions Work
- **Low traffic** (<10 events/second)
- **Single-process architecture** (one Lambda function, one server)
- **Batch processing** (non-real-time pipelines)
- **Testing/prototyping** (local development)

---

## Alternative 1: PostgreSQL for Everything

### Implementation Pattern
Instead of Redis, use PostgreSQL for rate limiting and idempotency:

```python
# Rate limiting with PostgreSQL
async def check_rate_limit_pg(source: str, limit: int = 10):
    hour_bucket = datetime.now().strftime("%Y%m%d%H")
    
    # Increment counter in database
    async with pool.acquire() as conn:
        count = await conn.fetchval("""
            INSERT INTO rate_limits (source, hour_bucket, count)
            VALUES ($1, $2, 1)
            ON CONFLICT (source, hour_bucket)
            DO UPDATE SET count = rate_limits.count + 1
            RETURNING count
        """, source, hour_bucket)
        
        if count > limit:
            raise RateLimitExceeded()

# Idempotency with PostgreSQL
async def check_idempotency_pg(event_hash: str):
    async with pool.acquire() as conn:
        # Check if event already processed
        exists = await conn.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM idempotency_keys 
                WHERE event_hash = $1 
                AND created_at > NOW() - INTERVAL '1 hour'
            )
        """, event_hash)
        
        if exists:
            return True  # Already processed
        
        # Insert new key
        await conn.execute("""
            INSERT INTO idempotency_keys (event_hash, created_at)
            VALUES ($1, NOW())
        """, event_hash)
        
        return False
```

### Pros
✅ **One less infrastructure component** — No Redis to manage  
✅ **Permanent storage** — Data survives restarts  
✅ **Complex queries** — Can join with other tables  
✅ **Transaction guarantees** — Full ACID compliance  
✅ **Simpler operations** — Same tools/monitoring as main database

### Cons
❌ **Latency** — 5-50ms vs Redis <1ms  
❌ **Database load** — Hot-path queries hit main database  
❌ **Connection overhead** — Database connections are heavier than Redis  
❌ **No auto-expiry** — Need cleanup jobs for old keys  
❌ **Contention** — High-frequency updates can cause lock contention

### Performance Comparison
| Operation | PostgreSQL | Redis |
|-----------|-----------|-------|
| Rate limit check | 5-50ms | <1ms |
| Idempotency check | 10-30ms | <1ms |
| Concurrent writes | Locks required | Lock-free |
| Auto-cleanup | Cron job needed | TTL built-in |

### When PostgreSQL is Sufficient
```
Scenario: Batch processing pipeline
- 10 events/second average
- Processed asynchronously (not real-time)
- Single worker process

Decision: PostgreSQL only
Rationale: 50ms latency is acceptable when processing non-real-time.
           No shared state across processes.
```

### When Redis Becomes Necessary
```
Scenario: Real-time event processing
- 500 events/second peak
- 10 concurrent Lambda functions
- <100ms end-to-end latency requirement

Decision: Redis for hot-path, PostgreSQL for cold storage
Rationale: 50ms × 10 operations = 500ms database time per event.
           Redis keeps hot-path under 10ms total.
```

---

## Alternative 2: In-Memory Python Dictionary

### Implementation Pattern
For single-process applications, use Python's built-in data structures:

```python
from collections import defaultdict
from datetime import datetime
import time

class InMemoryCache:
    def __init__(self):
        self.rate_limits = defaultdict(int)
        self.idempotency_keys = {}
        self.ttl_tracker = {}
    
    def check_rate_limit(self, source: str, limit: int = 10):
        hour_bucket = datetime.now().strftime("%Y%m%d%H")
        key = f"{source}:{hour_bucket}"
        
        self.rate_limits[key] += 1
        
        if self.rate_limits[key] > limit:
            raise RateLimitExceeded()
    
    def check_idempotency(self, event_hash: str, ttl: int = 3600):
        # Cleanup expired keys
        now = time.time()
        self.idempotency_keys = {
            k: v for k, v in self.idempotency_keys.items()
            if self.ttl_tracker.get(k, 0) > now
        }
        
        if event_hash in self.idempotency_keys:
            return True  # Duplicate
        
        self.idempotency_keys[event_hash] = True
        self.ttl_tracker[event_hash] = now + ttl
        return False

# Global instance
cache = InMemoryCache()
```

### Pros
✅ **Zero infrastructure** — No external services  
✅ **Instant access** — Nanosecond latency (no network)  
✅ **Simple debugging** — Direct Python inspection  
✅ **Perfect for development** — No Redis installation needed

### Cons
❌ **Single process only** — Doesn't work with multiple workers/Lambdas  
❌ **Lost on restart** — All state disappears  
❌ **Memory bound** — No disk persistence  
❌ **Manual TTL cleanup** — Need to implement expiry logic  
❌ **No atomic operations** — Race conditions in async code

### When In-Memory Works
```
Scenario: Local development testing
- Single developer
- pytest test suite
- Mock data generation

Decision: In-memory Python dict
Rationale: Tests run in single process.
           Fast, no setup required.
           State reset between tests is desirable.
```

### Critical Limitation Example
```python
# PROBLEM: Race condition in async code
async def process_event_async(event):
    # Two concurrent coroutines might both pass this check
    if not cache.check_idempotency(event.id):
        await expensive_operation(event)  # Both might execute!

# With Redis, this is atomic:
is_duplicate = await redis.set(key, "1", nx=True, ex=3600)
if not is_duplicate:
    await expensive_operation(event)  # Only one succeeds
```

---

## Alternative 3: SQLite for Local State

### Implementation Pattern
Embedded database for single-machine deployments:

```python
import aiosqlite
from datetime import datetime

class SQLiteCache:
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
    
    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    source TEXT,
                    hour_bucket TEXT,
                    count INTEGER,
                    PRIMARY KEY (source, hour_bucket)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    event_hash TEXT PRIMARY KEY,
                    created_at INTEGER
                )
            """)
            await db.commit()
    
    async def check_rate_limit(self, source: str, limit: int = 10):
        hour_bucket = datetime.now().strftime("%Y%m%d%H")
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO rate_limits VALUES (?, ?, 1)
                ON CONFLICT(source, hour_bucket)
                DO UPDATE SET count = count + 1
            """, (source, hour_bucket))
            
            count = await db.execute_fetchall("""
                SELECT count FROM rate_limits
                WHERE source = ? AND hour_bucket = ?
            """, (source, hour_bucket))
            
            await db.commit()
            
            if count[0][0] > limit:
                raise RateLimitExceeded()
```

### Pros
✅ **File-based persistence** — Survives restarts  
✅ **No server needed** — Embedded in application  
✅ **SQL queries** — Complex lookups possible  
✅ **Single machine shared state** — Multiple threads can share

### Cons
❌ **Write contention** — Single-writer database  
❌ **No distributed support** — Can't share across machines  
❌ **Manual TTL** — No automatic expiry  
❌ **Slower than Redis** — 1-10ms vs <1ms

### When SQLite Makes Sense
```
Scenario: Desktop application or single-server deployment
- Monolithic architecture (one server)
- Moderate traffic (<1000 req/sec)
- Persistence matters (survive restarts)

Decision: SQLite for cache
Rationale: Simpler than Redis setup.
           Good enough performance.
           File-based backup/restore.
```

---

## Decision Matrix: Choosing the Right Tool

### Traffic & Latency Requirements

| Traffic/Second | Latency SLA | Recommendation |
|----------------|-------------|----------------|
| <10 | >100ms | PostgreSQL only |
| 10-100 | >50ms | PostgreSQL or SQLite |
| 100-1000 | >10ms | Redis recommended |
| >1000 | <10ms | Redis required |

### Architecture Patterns

| Pattern | Best Choice | Reason |
|---------|-------------|--------|
| Single Lambda function (low traffic) | PostgreSQL | No shared state needed |
| Multiple Lambda functions | Redis | Shared state across invocations |
| Monolithic server (one instance) | PostgreSQL or SQLite | Single process can use locks |
| Distributed servers (multiple) | Redis | Cross-server coordination |
| Kubernetes/ECS (multi-pod) | Redis | Pods need shared cache |

### Data Characteristics

| Characteristic | PostgreSQL | Redis | In-Memory |
|----------------|-----------|-------|-----------|
| Must survive restart | ✅ | ❌ | ❌ |
| TTL auto-cleanup | ❌ | ✅ | ❌ |
| Sub-millisecond latency | ❌ | ✅ | ✅ |
| Complex queries | ✅ | ❌ | ❌ |
| Distributed access | ✅ | ✅ | ❌ |

---

## Our Decision: Why We Chose Redis

### Project Context
- **Architecture**: AWS Lambda functions (multiple concurrent invocations)
- **Traffic expectations**: 100-500 events/second at peak
- **Latency requirement**: <100ms end-to-end processing
- **Use cases**: Rate limiting, idempotency, session tracking

### Decision Rationale

```
Given:
1. Multiple Lambda instances running concurrently
2. Need to enforce global rate limits (not per-Lambda)
3. Idempotency checks must be atomic across instances
4. Event processing budget: 100ms total
   - Decision agent: ~40ms (LLM call)
   - Critic agent: ~40ms (LLM call)
   - Database operations: ~10ms
   - Cache operations: Must be <10ms total

Conclusion:
- PostgreSQL would add 5-50ms per cache operation
- With 3-5 cache operations per event, that's 15-250ms just for caching
- Exceeds our latency budget
- Redis keeps cache operations under 5ms total
- Trade-off: One more infrastructure component, but necessary for performance
```

### Why Not Alternatives?

**PostgreSQL only**:
- ❌ Would hit database for every rate limit check (500/second = unsustainable load)
- ❌ Latency would violate our <100ms SLA
- ✅ Could work if we relaxed requirements to <500ms and <50 events/second

**In-memory Python**:
- ❌ Lambda functions are stateless — each invocation is isolated
- ❌ Can't share rate limit counters across concurrent Lambdas
- ✅ Could work for single-instance deployments

**SQLite**:
- ❌ Can't share across Lambda invocations (each has own filesystem)
- ❌ Lambda has read-only filesystem (except /tmp)
- ✅ Could work for EC2/ECS deployments

### Cost-Benefit Analysis

**Redis Cost**:
- Infrastructure: ~$15/month (ElastiCache) or ~$5/month (Upstash free tier)
- Operational: Monitoring, connection management
- Learning curve: Team needs Redis knowledge

**Redis Benefit**:
- Performance: 50x faster than PostgreSQL for hot-path operations
- Scale: Handles 10K-100K ops/second without breaking a sweat
- Reliability: Built-in TTL prevents key accumulation
- Atomic operations: Lock-free rate limiting and idempotency

**ROI**: For production AI systems, the performance gain justifies the infrastructure cost.

---

## Real-World Scenarios & Examples

### Scenario 1: Monitoring System (High Traffic)

**Context**: Security monitoring receiving 1000 events/second from various sources.

**Problem**: Need to rate-limit each source to 100 events/minute to prevent spam.

**Solution Comparison**:

```python
# PostgreSQL approach
async def rate_limit_pg():
    # 1000 events/sec × 5-50ms DB latency = 5-50 seconds of DB time/second
    # Impossible — database saturated
    pass

# Redis approach  
async def rate_limit_redis():
    # 1000 events/sec × <1ms Redis latency = 1 second of Redis time/second
    # Easily handled by single Redis instance
    await redis.incr(f"rate:{source}:{minute}")
```

**Decision**: Redis required. PostgreSQL cannot handle the throughput.

---

### Scenario 2: Batch Processing Pipeline (Low Traffic)

**Context**: Nightly batch job processing 10,000 events over 1 hour.

**Problem**: Prevent duplicate processing of same event.

**Solution Comparison**:

```python
# PostgreSQL approach
async def check_duplicate_pg(event_id):
    # 10,000 events / 3600 seconds = 2.7 events/second
    # 50ms DB latency is fine — not on critical path
    exists = await db.fetchval(
        "SELECT EXISTS(SELECT 1 FROM processed_events WHERE id = $1)",
        event_id
    )
    if exists:
        return True
    await db.execute("INSERT INTO processed_events (id) VALUES ($1)", event_id)
    return False
```

**Decision**: PostgreSQL sufficient. No need for Redis infrastructure.

---

### Scenario 3: API Gateway (Medium Traffic)

**Context**: REST API with 50 requests/second, need to rate-limit by API key.

**Problem**: 100 requests/minute per API key.

**Solution Comparison**:

**Option 1: PostgreSQL with connection pooling**
```python
# Acceptable if:
# - Using connection pool (reuse connections)
# - Database has spare capacity
# - 10-20ms added latency is OK

async def rate_limit_pg(api_key: str):
    minute_bucket = datetime.now().strftime("%Y%m%d%H%M")
    count = await pool.fetchval("""
        INSERT INTO api_rate_limits VALUES ($1, $2, 1)
        ON CONFLICT DO UPDATE SET count = count + 1
        RETURNING count
    """, api_key, minute_bucket)
    return count <= 100
```

**Option 2: Redis**
```python
# Preferred if:
# - Want to offload database
# - <5ms latency desired
# - Planning to scale beyond 100 req/sec

async def rate_limit_redis(api_key: str):
    minute_bucket = datetime.now().strftime("%Y%m%d%H%M")
    key = f"api_rate:{api_key}:{minute_bucket}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 120)  # Auto-cleanup
    return count <= 100
```

**Decision**: Either works. Choose Redis if you expect to scale or want to keep database light.

---

### Scenario 4: Machine Learning Inference Cache

**Context**: LLM API calls cost $0.01 each. Same prompts often repeated.

**Problem**: Cache responses to avoid duplicate LLM calls.

**Solution**:

```python
import hashlib

async def get_llm_response(prompt: str, model: str):
    # Cache key from prompt hash
    cache_key = f"llm_cache:{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"
    
    # Check Redis first
    cached = await redis.get(cache_key)
    if cached:
        logger.info("Cache hit — saved $0.01")
        return json.loads(cached)
    
    # Call LLM
    response = await call_openai(prompt, model)
    
    # Cache for 1 hour
    await redis.setex(cache_key, 3600, json.dumps(response))
    
    return response
```

**Why Redis here**:
- ✅ Fast cache lookups (<1ms)
- ✅ TTL auto-cleanup (no stale responses)
- ✅ Can handle high cache hit rates
- ❌ PostgreSQL would work but slower and needs manual cleanup

**ROI**: If cache hit rate is 50%, saves $0.005 per request. At 1000 requests/day, that's $5/day = $150/month saved. Redis costs $15/month. **10x ROI**.

---

## When Low Latency Doesn't Matter

### Batch Processing
```python
# Processing historical data — no real-time requirement
async def process_historical_events():
    events = await db.fetch("SELECT * FROM events WHERE processed = false")
    
    for event in events:
        # 50ms database lookup is fine here
        if await db.fetchval("SELECT EXISTS(SELECT 1 FROM duplicates WHERE hash = $1)", event.hash):
            continue
        
        # Process event...
        await process_event(event)
```

**No Redis needed**: Not on critical path, throughput doesn't justify infrastructure.

### Asynchronous Workflows
```python
# Background job triggered by queue
async def background_worker():
    while True:
        event = await queue.get()  # Already decoupled from user request
        
        # User doesn't care if this takes 100ms or 1000ms
        await db.execute("INSERT INTO analytics ...")
        await db.execute("UPDATE metrics ...")
```

**No Redis needed**: Latency doesn't affect user experience.

### Admin Dashboards
```python
# Admin viewing dashboard — 500ms page load is acceptable
async def get_dashboard_stats():
    # Complex query, 200ms is fine
    stats = await db.fetch("""
        SELECT 
            COUNT(*) as events,
            AVG(confidence) as avg_confidence
        FROM events
        WHERE created_at > NOW() - INTERVAL '1 day'
        GROUP BY source
    """)
    return stats
```

**No Redis needed**: Humans don't perceive <1 second latency for page loads.

---

## Migration Path: Start Simple, Add Redis Later

### Phase 1: PostgreSQL Only (MVP)
```python
# Start with database for everything
class SimpleCache:
    async def check_rate_limit(self, source: str):
        # Use PostgreSQL, measure latency
        return await db.fetchval("...")

# Deploy, measure, monitor
```

### Phase 2: Identify Bottlenecks
```python
# Add logging to measure latency
import time

async def check_rate_limit(self, source: str):
    start = time.time()
    result = await db.fetchval("...")
    latency_ms = (time.time() - start) * 1000
    
    if latency_ms > 10:
        logger.warning(f"Slow rate limit check: {latency_ms}ms")
    
    return result
```

### Phase 3: Selective Redis (Optimize Hot Path)
```python
# Add Redis only for proven bottlenecks
class HybridCache:
    async def check_rate_limit(self, source: str):
        # Hot path → Redis
        return await redis.incr(f"rate:{source}")
    
    async def get_historical_stats(self):
        # Cold path → PostgreSQL (complex query)
        return await db.fetch("SELECT ... GROUP BY ...")
```

**Key insight**: Don't over-engineer early. Add Redis when you have evidence it's needed.

---

## Summary: The Redis Decision Framework

### Ask These Questions

1. **Is this on the critical path?**
   - Yes → Consider Redis
   - No → PostgreSQL is fine

2. **What's the throughput?**
   - >100 ops/second → Redis
   - <100 ops/second → PostgreSQL likely OK

3. **Is it distributed?**
   - Multiple processes/Lambdas → Redis
   - Single process → In-memory or SQLite

4. **Can we afford to lose the data?**
   - Yes (rate limits, caches) → Redis is perfect
   - No (events, audit logs) → PostgreSQL required

5. **Do we need atomic operations?**
   - Yes (counters, locks) → Redis (INCR, SETNX)
   - No → Any solution works

### For This Project

| Component | Storage | Justification |
|-----------|---------|---------------|
| Events | PostgreSQL | Source of truth, must persist |
| Decisions | PostgreSQL | Audit requirement, complex queries |
| Rate limits | **Redis** | Hot path, high throughput, atomic increment |
| Idempotency | **Redis** | Hot path, atomic check-and-set, TTL cleanup |
| LLM cache | **Redis** | Cost savings, TTL expiry, fast lookups |
| Analytics | PostgreSQL | Complex queries, not latency-sensitive |

---

## The Bottom Line

> **Redis is not a hammer, and not everything is a nail.**

Use Redis when:
- ✅ Latency is critical (<10ms)
- ✅ Throughput is high (>100 ops/sec)
- ✅ Data can be lost without catastrophe
- ✅ Multiple processes need shared state

Don't use Redis when:
- ❌ PostgreSQL latency is acceptable
- ❌ Traffic is low enough for database
- ❌ Single-process architecture
- ❌ Data must survive restarts

**For agentic AI systems at production scale**: Redis is worth the infrastructure investment. The performance gains in rate limiting, idempotency, and caching directly impact system reliability and cost efficiency.
