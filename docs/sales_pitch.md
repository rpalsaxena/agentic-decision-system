# Sales Pitch & Use Cases: Agentic AI Decision System

**Purpose**: Quick reference for founder/CTO conversations (5-10 min)

---

## 30-Second Elevator Pitch

> "I built a production-grade agentic AI system for operational decision-making. The model recommends; the system enforces safety, confidence thresholds, and audit trails. It runs on AWS — PostgreSQL, Redis, Pinecone — with real observability. Not a demo. A deployable system."

---

## 2-Minute Version

> "Most companies drown in operational signals. Humans can't triage 24/7.
>
> I built an AI system that:
> - **Classifies** events and **recommends** actions with confidence
> - **Self-critiques** and **defers** when uncertain
> - Runs on **production infrastructure** — AWS RDS, ElastiCache, Pinecone
>
> The key insight: the danger isn't automation — it's **overconfident AI**. So I built the control layer first: rate limits, confidence gates, audit logs, output validation.
>
> Built in 45 hours. v1 in Python, v2 with LangGraph. Ready for real workloads."

---

## Industry Use Cases

### DevOps / SRE
| Signal | AI Action |
|--------|-----------|
| Latency spike | Assess severity, recommend alert |
| Deploy failure | Classify cause, suggest rollback |
| Error rate spike | Correlate with changes |

### Customer Success
| Signal | AI Action |
|--------|-----------|
| Churn risk | Recommend outreach |
| Ticket spike | Classify theme, escalate |

### Security Operations
| Signal | AI Action |
|--------|-----------|
| Suspicious login | Risk assessment |
| Data access anomaly | Flag investigation |

---

## Technical Highlights

| Component | Implementation |
|-----------|----------------|
| Database | AWS RDS PostgreSQL |
| Distributed state | AWS ElastiCache Redis |
| Vector search | Pinecone (free tier) |
| Observability | AWS CloudWatch |
| Orchestration | LangGraph (v2) |

---

## FAQ

### "How long did this take?"
> "45 hours. v1 in Python, v2 with LangGraph migration. Runs on AWS infrastructure."

### "What makes this different from agent demos?"
> "Mine assumes the LLM is untrusted. System enforces safety — rate limits, confidence gates, output validation. Most demos are impressive but unsafe."

### "What's the accuracy?"
> "75%+ correct, <10% false positives, 15-25% abstention. Confidence is calibrated."

### "Can it scale?"
> "PostgreSQL, Redis, Pinecone are all horizontally scalable. The architecture is stateless."

---

## What This Demonstrates

| Skill | Evidence |
|-------|----------|
| Production AI | Safety-first, cloud infrastructure |
| Agentic systems | Multi-agent with governance |
| Cloud engineering | AWS RDS, ElastiCache, Pinecone |
| Speed | 45 hours end-to-end |

---

## Closing Line

> "I built something deployable, not just impressive. Production infrastructure, real evaluation metrics, and safety by design."
