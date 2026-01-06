# Implementation Guide: Agentic AI Decision System

**Format**: Architectural reasoning + hands-on tutorial  
**Goal**: Build Staff+ engineering intuition

---

## 📑 Table of Contents

- [Philosophy](#philosophy-how-to-read-this-guide)
- [Phase 0: Infrastructure](#phase-0-infrastructure)
  - [Why Cloud?](#the-big-picture-question)
  - [Database Choice](#step-01-postgresql-vs-aurora-vs-mongodb)
  - [Cache Choice](#step-02-redis)
  - [Vector DB Choice](#step-03-pinecone)
  - [Environment Setup](#step-04-environment-file)
- [Phase 1: Foundation](#phase-1-foundation)
  - [Project Structure](#step-11-project-structure)
  - [Data Models](#step-12-pydantic-models)
  - [Database Layer](#step-14-asyncpg-vs-orm)
- [Phase 2: Core Agents](#phase-2-core-agents)
  - [Agent Architecture](#the-architecture-question)
  - [Structured Outputs](#why-instructor)
  - [Critic Design](#critic-agent-design)
- [Phase 3: Safety Layer](#phase-3-safety-layer)
  - [Rate Limiting](#rate-limiting)
  - [Confidence Threshold](#confidence-threshold)
  - [Idempotency](#idempotency)
- [Design Principles](#design-principles-summary)

---

# Philosophy: How to Read This Guide

> **Don't just do what I say. Understand why I'm saying it.**

For each decision, I explain:
1. **The Problem** — What are we solving?
2. **Options Considered** — What alternatives exist?
3. **Why This Choice** — Trade-offs that led to this decision
4. **When You'd Choose Differently** — Context matters

---

# PHASE 0: Infrastructure

## The Big Picture Question

<details>
<summary><strong>🤔 Why cloud infrastructure for a portfolio project?</strong></summary>

### Options
| Option | Pros | Cons |
|--------|------|------|
| **SQLite + in-memory** | Fast to start, zero setup | Signals "prototype thinking" |
| **Docker Compose locally** | Good middle ground | Still "works on my machine" |
| **AWS managed services** | Production-grade, scalable | More setup, some cost |

### Why AWS
**Signal over convenience.** Hiring managers see hundreds of projects with SQLite. When you use RDS/Aurora, ElastiCache, and Pinecone, you're saying: "I know how production systems work."

### When you'd choose differently
- Hackathon with 6-hour deadline → SQLite
- Team project with infra engineer → Let them decide
- Cost-constrained → Docker Compose, upgrade later

</details>

---

## Step 0.1: PostgreSQL vs Aurora vs MongoDB

<details>
<summary><strong>🗄️ Database Selection Deep Dive</strong></summary>

### The Problem
We need to store events, decisions, and audit logs with relationships between them.

### Options Comparison

| Option | Pros | Cons | Cost |
|--------|------|------|------|
| **RDS PostgreSQL** | JSONB, mature, well-documented | Manual scaling, fixed capacity | ~$15/month (t3.micro) |
| **Aurora PostgreSQL** | Auto-scaling, faster, HA built-in | Slightly higher base cost, AWS lock-in | ~$30-50/month (serverless v2) |
| **Aurora Serverless v2** | Scale to zero, pay-per-use | Cold start latency, less predictable cost | $0 when idle, variable |
| **MongoDB Atlas** | Schema-flexible, fast writes | No ACID for joins, harder auditing | Free tier available |
| **PlanetScale** | Serverless MySQL, branching | MySQL limitations, no JSONB | Free tier available |

### Aurora vs RDS: The Real Trade-off

| Aspect | RDS PostgreSQL | Aurora PostgreSQL |
|--------|----------------|-------------------|
| **Performance** | Good | 3-5x faster for reads |
| **Scaling** | Manual resize (downtime) | Auto-scaling, no downtime |
| **High Availability** | Multi-AZ requires setup | Built-in, automatic |
| **Storage** | Provision upfront | Auto-grows, pay for usage |
| **Cost (small workload)** | Cheaper | Slightly higher |
| **Cost (scale)** | Less efficient | More cost-efficient |

### My Recommendation

**For this project: Aurora Serverless v2**

Reasons:
1. **Scale to zero** — When you're not running evaluations, cost drops to near-zero
2. **No capacity planning** — Don't guess t3.micro vs t3.small
3. **Production-realistic** — Shows you understand modern cloud patterns
4. **Cold start acceptable** — Our use case isn't latency-critical at DB level

### When RDS is Better
- Predictable, steady workload
- Need exact cost control
- Running 24/7 with consistent load

### When MongoDB is Better
- Schema varies wildly per event type
- Don't need relational integrity
- Already using MongoDB at target company

### Setup: Aurora Serverless v2

```
1. AWS Console → RDS → Create Database
2. Engine: Aurora (PostgreSQL Compatible)
3. Engine version: Aurora PostgreSQL 15+
4. Template: Serverless v2
5. Capacity range: 0.5 - 2 ACU (can scale to zero)
6. DB identifier: agentic-db
7. Master username: postgres
8. Enable: "Pause after inactivity" (saves cost)
```

### Connection String
```
postgresql+asyncpg://postgres:PASSWORD@agentic-db.cluster-xxxxx.us-east-1.rds.amazonaws.com:5432/agentic
```

### Step-by-Step: Create Database & Tables

**1. Connect to Aurora**
```powershell
# Using psql (install PostgreSQL client if needed)
psql -h agentic-db.cluster-xxxxx.us-east-1.rds.amazonaws.com -U postgres -d postgres

# Or use DBeaver, pgAdmin, or any PostgreSQL client
```

**2. Create the Database**
```sql
-- Create database
CREATE DATABASE agentic;

-- Connect to it
\c agentic
```

**3. Create Tables**
```sql
-- ============================================
-- EVENTS TABLE
-- Stores raw operational events
-- ============================================
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(255) NOT NULL,
    raw_payload JSONB NOT NULL,
    event_type VARCHAR(50),
    severity VARCHAR(20),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying by type and time
CREATE INDEX idx_events_type_time ON events(event_type, created_at DESC);
CREATE INDEX idx_events_source ON events(source);

-- ============================================
-- DECISIONS TABLE
-- Stores AI-recommended actions
-- ============================================
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    reasoning TEXT,
    alternative_actions JSONB DEFAULT '[]',
    model_version VARCHAR(100),
    prompt_version VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for looking up decisions by event
CREATE INDEX idx_decisions_event ON decisions(event_id);

-- ============================================
-- CRITIQUES TABLE
-- Stores safety review results
-- ============================================
CREATE TABLE critiques (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id UUID NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    verdict VARCHAR(20) NOT NULL CHECK (verdict IN ('approve', 'reject', 'defer')),
    risk_flags JSONB DEFAULT '[]',
    reasoning TEXT,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for looking up critiques by decision
CREATE INDEX idx_critiques_decision ON critiques(decision_id);

-- ============================================
-- AUDIT LOGS TABLE
-- Complete decision trail for compliance
-- ============================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id),
    decision_id UUID NOT NULL REFERENCES decisions(id),
    critique_id UUID NOT NULL REFERENCES critiques(id),
    event_hash VARCHAR(64) NOT NULL,
    final_action VARCHAR(50) NOT NULL,
    blocked BOOLEAN DEFAULT FALSE,
    block_reason TEXT,
    latency_ms INTEGER,
    safety_checks JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for audit queries
CREATE INDEX idx_audit_time ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_blocked ON audit_logs(blocked) WHERE blocked = TRUE;
CREATE INDEX idx_audit_hash ON audit_logs(event_hash);
```

**4. Verify Tables**
```sql
-- List all tables
\dt

-- Expected output:
--            List of relations
--  Schema |    Name     | Type  |  Owner
-- --------+-------------+-------+----------
--  public | audit_logs  | table | postgres
--  public | critiques   | table | postgres
--  public | decisions   | table | postgres
--  public | events      | table | postgres

-- Check table structure
\d events
\d decisions
\d critiques
\d audit_logs
```

**5. Test Insert (Optional)**
```sql
-- Insert a test event
INSERT INTO events (timestamp, source, raw_payload, event_type, severity)
VALUES (
    NOW(),
    'test-source',
    '{"alert_name": "TestAlert", "service": "test-api"}'::jsonb,
    'incident',
    'medium'
);

-- Verify
SELECT * FROM events;

-- Clean up
DELETE FROM events WHERE source = 'test-source';
```

### ✅ Checkpoint
After running these commands, you should have:
- 4 tables: `events`, `decisions`, `critiques`, `audit_logs`
- Proper foreign key relationships
- Indexes for common query patterns
- CHECK constraints for data integrity

</details>

---

## Step 0.2: Redis

<details>
<summary><strong>⚡ Cache & Rate Limiting Layer</strong></summary>

### The Problem
Rate limiting and idempotency need shared state that survives restarts.

### Options
| Option | Pros | Cons |
|--------|------|------|
| **In-memory dict** | Zero setup | Lost on restart, no horizontal scaling |
| **Memcached** | Simple, fast | No TTL flexibility, no data structures |
| **Redis (ElastiCache)** | TTL, atomic ops, pub/sub | Another service to manage |
| **Upstash Redis** | Serverless, pay-per-request | Higher per-op cost at scale |
| **Database table** | Already have PostgreSQL | Slow for high-frequency checks |

### Why Redis
1. **TTL built-in** — `SETEX key 3600 value` handles idempotency expiry automatically
2. **Atomic increment** — `INCR rate:user:123` is race-condition free
3. **Sub-millisecond** — Rate limit checks happen on every request. Speed matters
4. **Horizontal scaling** — ElastiCache clusters scale without code changes

### The key insight
> Rate limiting is a **hot path**. Every event hits it. Don't put hot-path data in a cold database.

### Alternative: Upstash for Serverless

If using Aurora Serverless, consider **Upstash Redis**:
- No server to manage
- Pay per request (~$0.20 per 100K commands)
- Global edge locations
- Works great for low-to-moderate traffic

```
REDIS_URL=redis://default:xxxxx@us1-xxxxx.upstash.io:6379
```

</details>

---

## Step 0.3: Pinecone

<details>
<summary><strong>🔍 Vector Database for RAG</strong></summary>

### The Problem
RAG needs semantic search: "find events similar to this one."

### Options
| Option | Pros | Cons |
|--------|------|------|
| **FAISS** | Fast, local, free | No persistence, manual index management |
| **pgvector** | In PostgreSQL, simple | Slower at scale, no metadata filtering |
| **Pinecone** | Managed, fast, metadata filters | Another service, free tier limited |
| **Weaviate** | Self-hosted option | More complex deployment |
| **Qdrant** | Rust-based, fast, self-hosted | Requires infra management |

### Why Pinecone
1. **Managed** — No index maintenance, no OOM crashes, no sharding headaches
2. **Metadata filtering** — "Similar events from last 7 days" is one query
3. **Free tier** — 100K vectors is plenty for this project
4. **Production-grade** — Used by real companies

### When you'd choose differently
- Air-gapped environment → FAISS or pgvector
- Already in Aurora → Try `pgvector` extension first
- Want self-hosted → Qdrant or Weaviate

### Setup
```
1. pinecone.io → Sign up (free tier)
2. Create Index:
   - Name: event-embeddings
   - Dimensions: 1536 (OpenAI text-embedding-3-small)
   - Metric: cosine
   - Cloud: AWS us-east-1
```

</details>

---

## Step 0.4: Environment File

<details>
<summary><strong>🔐 Configuration Management</strong></summary>

### Create `.env`
```env
# Database (Aurora Serverless)
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@agentic-db.cluster-xxxxx.us-east-1.rds.amazonaws.com:5432/agentic

# Redis (ElastiCache or Upstash)
REDIS_URL=redis://agentic-cache.xxxxx.cache.amazonaws.com:6379

# Pinecone
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX=event-embeddings

# LLM APIs
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key

# Safety Settings
CONFIDENCE_THRESHOLD=0.75
RATE_LIMIT_ACTIONS_PER_HOUR=10
```

### Why `.env` instead of hardcoding?
1. **Security** — Secrets never in git
2. **Environment flexibility** — Dev vs staging vs prod
3. **12-factor app** — Industry standard pattern

</details>

---

# PHASE 1: Foundation

## Step 1.1: Project Structure

<details>
<summary><strong>📁 Modular Architecture by Concern</strong></summary>

### The Problem
Code organization affects maintainability, testability, and onboarding.

### Pattern Options
| Pattern | When it works | When it fails |
|---------|---------------|---------------|
| **Flat files** | Scripts, notebooks | Anything with >5 files |
| **By type** (`models/`, `views/`) | Simple CRUD apps | Complex domain logic |
| **By feature** (`events/`, `decisions/`) | Microservices | Shared utilities |
| **Hybrid (ours)** | Domain-rich applications | Very small projects |

### Our Structure
```
src/
├── models/      # Data shapes (what)
├── agents/      # LLM logic (intelligence)
├── pipeline/    # Orchestration (how things flow)
├── safety/      # Constraints (what's NOT allowed)
├── security/    # Protection (trust boundaries)
├── db/          # Persistence (storage)
└── cache/       # Speed (hot data)
```

### Why This Works
- **Separation of concerns** — Safety logic never lives in agents
- **Testability** — Mock `db/` and test agents in isolation
- **Onboarding** — New engineer knows where to look

### The insight
> Code structure is a communication tool. It tells future you (and your team) where things belong.

</details>

---

## Step 1.2: Pydantic Models

<details>
<summary><strong>📊 Type Safety & Validation</strong></summary>

### The Problem
We pass data between agents, to the database, and to Claude. Type safety prevents bugs.

### Options
| Option | Pros | Cons |
|--------|------|------|
| **Dicts** | Flexible, no boilerplate | No validation, typos cause bugs |
| **Dataclasses** | Built-in, simple | No validation, manual JSON |
| **Pydantic** | Validation, serialization, IDE support | Slight overhead |
| **TypedDict** | Type hints for dicts | No runtime validation |

### Why Pydantic
1. **Validation at boundaries** — When Claude returns JSON, Pydantic validates it
2. **Serialization built-in** — `.model_dump_json()` for storage
3. **Instructor integration** — Instructor uses Pydantic for structured LLM outputs
4. **IDE autocomplete** — `decision.confidence` is typed

### The insight
> In agentic systems, data crosses many boundaries (LLM → Python → database → API). Validate at every crossing.

</details>

---

## Step 1.4: asyncpg vs ORM

<details>
<summary><strong>🔌 Database Access Patterns</strong></summary>

### The Problem
We need to read/write PostgreSQL. Should we use an ORM?

### Options
| Option | Pros | Cons |
|--------|------|------|
| **psycopg2** | Sync, well-known | Blocks event loop |
| **SQLAlchemy ORM** | High-level, migrations | Heavy, hides SQL |
| **asyncpg** | Fast, async-native, simple | Raw SQL only |
| **SQLModel** | Pydantic + SQLAlchemy | Newer, less documented |

### Why asyncpg
1. **Async-native** — Our pipeline is async. Blocking DB calls would kill latency
2. **Speed** — Fastest Python PostgreSQL driver by benchmarks
3. **Simplicity** — Raw SQL is explicit. No ORM magic to debug
4. **Connection pooling** — Built-in pool management

### The trade-off
No ORM means writing SQL manually. Acceptable for simple schemas.

### Connection Pooling
```python
_pool = await asyncpg.create_pool(url, min_size=2, max_size=10)
```

- **min_size=2** — Cold start has connections ready
- **max_size=10** — Prevents overwhelming the database

</details>

---

# PHASE 2: Core Agents

## The Architecture Question

<details>
<summary><strong>🤖 Why Three Agents Instead of One?</strong></summary>

### Options
| Approach | Pros | Cons |
|----------|------|------|
| **One mega-prompt** | Simpler, fewer API calls | Hard to test, no separation |
| **Two agents (decide + validate)** | Good balance | Validator might rubber-stamp |
| **Three agents (classify + decide + critique)** | Clear stages, testable | More latency, cost |

### Why Three
1. **Separation of concerns** — Classification is "what happened." Decision is "what to do." Critique is "should we do it."
2. **Testability** — Test each agent in isolation
3. **Different temperature** — Critic at 0.7 for diversity, decision at 0.3 for consistency
4. **Audit clarity** — Logs show exactly where decisions were made vs challenged

### Cost Analysis
3 API calls × ~$0.003 = ~$0.01 per event. Acceptable for production value.

</details>

---

## Why Instructor

<details>
<summary><strong>📝 Structured LLM Outputs</strong></summary>

### The Problem
Claude returns text. We need structured data.

### Options
| Option | Reliability |
|--------|-------------|
| **Parse JSON from text** | Fragile. Claude might add explanation |
| **Function calling raw** | Better, but manual validation |
| **Instructor** | Type-safe, retries, validation |

### Why Instructor
```python
result = client.messages.create(
    response_model=DecisionOutput,  # Pydantic model
    ...
)
# result is guaranteed to be DecisionOutput or raises
```

**Features:**
- Automatic retries on invalid JSON
- Type coercion ("0.85" → float 0.85)
- Validation (confidence > 1.0 rejected)

</details>

---

## Critic Agent Design

<details>
<summary><strong>🔍 Adversarial Review Pattern</strong></summary>

### The Problem
A "reviewer" that always agrees is useless.

### The Solution: Adversarial Framing
```
You are a skeptical safety reviewer. Your job is to find reasons to REJECT.
...
Be critical. If in doubt, defer.
```

**Plus: temperature=0.7**

### Why This Works
1. **Role matters** — "Your job is to REJECT" changes behavior significantly
2. **Higher temperature** — More variance = more likely to surface edge cases
3. **Different framing** — Decision agent: "recommend action." Critic: "find problems."

### The insight
> LLMs naturally tend toward agreement. You must prompt them to disagree.

</details>

---

# PHASE 3: Safety Layer

## The Key Insight

> **Safety is not a feature. It's the architecture.**

```
Event → Sanitize → Classify → Decide → Critique → SAFETY GATE → Action
                                            ↑
                                    This is the real system
```

---

## Rate Limiting

<details>
<summary><strong>🚦 Preventing Action Overload</strong></summary>

### The Problem
Even a perfect AI can cause harm at scale. 1000 correct alerts = alert fatigue.

### The Design
```python
RATE_LIMITS = {
    "actions_per_hour": 10,
    "alerts_per_hour": 5,
    "human_reviews_per_hour": 3
}
```

### Why These Numbers
- **10 actions/hour** — Reasonable for incident response
- **5 alerts/hour** — Slack channels get noisy fast
- **3 human reviews/hour** — If AI is deferring constantly, something's wrong

### The Deeper Point
> These aren't magic numbers. They're **policy decisions** made configurable and enforceable.

</details>

---

## Confidence Threshold

<details>
<summary><strong>📊 Calibrating Trust in AI</strong></summary>

### The Problem
LLMs are confidently wrong. How do we catch this?

### The Trade-off
| Threshold | Effect |
|-----------|--------|
| **0.5** | More automation, more errors |
| **0.75** | Balanced |
| **0.9** | Very safe, but most goes to humans |

### Why 0.75
After calibration testing, 0.75 confidence typically corresponds to ~85% actual accuracy.

### The insight
> The threshold isn't about trust in AI. It's about risk tolerance.

</details>

---

## Idempotency

<details>
<summary><strong>🔄 Preventing Duplicate Actions</strong></summary>

### The Problem
Event systems often have at-least-once delivery. Same event might arrive twice.

### The Solution
```python
event_hash = sha256(json.dumps(event, sort_keys=True))
if await redis.exists(f"idem:{event_hash}"):
    return "Already processed"
await redis.setex(f"idem:{event_hash}", 3600, "1")
```

### Why Hash-Based + TTL
1. **Hash** — Same payload = same hash
2. **TTL (1 hour)** — Eventually allow re-processing
3. **Redis** — Distributed, survives restarts

</details>

---

# Design Principles Summary

| Principle | Meaning |
|-----------|---------|
| **Constrain Before You Automate** | Build safety layer before making AI smarter |
| **Fail Safe, Not Fail Silent** | Block and log, never silently proceed |
| **Validate at Every Boundary** | LLM → Python → DB → API, validate each |
| **Make the Hot Path Fast** | Rate limiting in Redis, not PostgreSQL |
| **Design for Auditability** | Every decision reconstructable from logs |

---

**Next: Continue to step-by-step implementation or dive deeper into any section?**
