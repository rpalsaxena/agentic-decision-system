# Project Overview: Agentic AI Decision System

**Project Type**: Portfolio/Demonstration Project  
**Domain**: AI Safety & Operational Automation  
**Target Audience**: Hiring managers at AI-native companies (Series A-C)

---

## Executive Summary

This project demonstrates production-grade thinking in agentic AI systems by building a **safe, bounded decision-making system** for operational events. Unlike typical AI demos that prioritize impressive capabilities, this system prioritizes **safety, auditability, and human oversight**.

**The Core Problem**: Companies receive hundreds of operational signals daily (incidents, errors, deploys). Humans can't monitor 24/7, but fully autonomous AI is too risky.

**Our Solution**: An AI system that recommends actions with confidence scores, self-critiques decisions, and defers to humans when uncertain — all while enforcing strict safety constraints.

---

## Problem Statement

### The Real-World Challenge

Modern engineering teams face alert fatigue:
- **100+ daily alerts** from monitoring systems
- **5-10 minutes per alert** to triage and decide action
- **24/7 coverage required** — humans get tired, miss patterns
- **Cost of mistakes**: False positives → alert fatigue, False negatives → incidents escalate

### Why Traditional Solutions Fall Short

| Approach | Problem |
|----------|---------|
| **Rule-based automation** | Brittle, can't handle novel situations |
| **Full AI autonomy** | Dangerous — no oversight, hard to audit |
| **Manual-only** | Doesn't scale, human fatigue |

### What We're Building Instead

**AI-assisted decision-making** where:
- AI handles classification and recommendation
- System enforces safety constraints
- Humans stay in the loop for high-stakes decisions
- Every decision is auditable

---

## Project Scope

### ✅ In Scope

| Component | What We're Building | Why It Matters |
|-----------|---------------------|----------------|
| **Event Classification** | Categorize events (incident, noise, etc.) | Reduces ambiguity early |
| **Decision Recommendation** | Suggest action with confidence score | Shows AI judgment |
| **Safety Critique** | Adversarial review of decisions | Catches overconfidence |
| **Safety Constraints** | Rate limits, confidence gates, idempotency | Production-grade safety |
| **Security Layer** | Input sanitization, output validation | Enterprise-ready |
| **RAG Context** | Retrieve similar past incidents | Improves decision quality |
| **Evaluation Framework** | 200 labeled events, calibration metrics | Proves it works |
| **Cloud Infrastructure** | Aurora, Redis, Pinecone | Shows deployment skills |

### ❌ Out of Scope

- Production UI (CLI only)
- Real integrations (Slack, Jira — all mocked)
- Multi-tenancy
- Model fine-tuning
- Auto-retraining
- High-availability deployment
- CI/CD pipeline

**Rationale**: This is a **portfolio project**, not a product. Focus is on demonstrating AI systems thinking, not building a complete SaaS.

---

## System Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Event Arrives                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Security Layer: Sanitize input, redact PII                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Agent 1: Classify (incident? noise? severity?)             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Agent 2: Decide (recommend action + confidence)            │
│  + RAG: Retrieve similar past events                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Agent 3: Critique (adversarial review, find risks)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Safety Gate: Check rate limits, confidence, policies       │
└─────────────────────────────────────────────────────────────┘
                            ↓
              ┌─────────────┴─────────────┐
              ↓                           ↓
    ┌──────────────────┐      ┌──────────────────┐
    │  Execute Action  │      │  Defer to Human  │
    │  (if approved)   │      │  (if uncertain)  │
    └──────────────────┘      └──────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Audit Log: Store complete decision trail                   │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Three Agents, Not One**
   - Separation of concerns: classify ≠ decide ≠ critique
   - Different temperatures for diversity
   - Easier to test and debug

2. **Safety Layer is System-Enforced**
   - Not in prompts (prompts can be jailbroken)
   - Hard constraints in code
   - Fail safe, not fail silent

3. **Sequential, Not Looping**
   - Predictable execution path
   - Bounded cost and latency
   - Auditable — every decision follows same flow

4. **LLM as Untrusted Component**
   - Validate all inputs and outputs
   - Assume adversarial responses
   - Never execute LLM output directly

---

## Technology Stack

### Core Technologies

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Language** | Python 3.11+ | Standard for AI/ML |
| **LLM** | Claude 3.5 Sonnet | Best structured output quality |
| **Structured Output** | Instructor + Pydantic | Type-safe LLM responses |
| **Database** | Aurora PostgreSQL Serverless v2 | Production-grade, scale-to-zero |
| **Cache** | Redis (Upstash) | Sub-ms rate limiting |
| **Vector DB** | Pinecone | Managed semantic search |
| **Orchestration (v2)** | LangGraph | Conditional routing, HITL |

### Why These Choices?

**Aurora over RDS**: Auto-scaling, scale-to-zero saves cost  
**Redis over in-memory**: Distributed state, survives restarts  
**Pinecone over FAISS**: Managed, no infra headaches  
**Instructor over raw API**: Automatic retries, validation  

---

## Success Metrics

### Decision Quality

| Metric | Target | Reject System If |
|--------|--------|------------------|
| Correct decision rate | ≥75% | <60% |
| False positive rate | ≤10% | >20% |
| Abstention rate | 15-30% | <5% or >50% |
| Confidence calibration (ECE) | <0.15 | >0.25 |

### Safety & Reliability

| Metric | Target | Notes |
|--------|--------|-------|
| Safety blocks triggered | 2-5% | 0% means safety layer isn't working |
| Prompt injection blocked | 100% | Any success is a failure |
| Critic disagreement rate | 15-25% | Too low = rubber-stamping |
| Latency P95 | <3s | Operational systems need speed |

### What "Good Enough" Looks Like

- 75%+ correct decisions on held-out test set
- Confidence scores correlate with actual accuracy
- All safety policies demonstrably enforced
- Clear audit trail for every decision
- Can explain any decision to a human in <30 seconds

---

## User Stories

### Primary Persona: DevOps Engineer

**Story 1: Incident Triage**
> As a DevOps engineer, I want the system to classify incoming alerts so I can focus on real incidents, not noise.

**Acceptance Criteria**:
- System correctly identifies "noise" events (health checks, routine logs)
- System flags high-severity incidents for immediate attention
- Classification includes reasoning I can verify

---

**Story 2: Action Recommendation**
> As a DevOps engineer, I want the system to recommend actions with confidence scores so I can trust its judgment.

**Acceptance Criteria**:
- System recommends one of: send_alert, create_ticket, do_nothing, request_human_review
- Confidence score reflects actual accuracy (calibrated)
- Reasoning explains why this action was chosen

---

**Story 3: Safety Override**
> As a DevOps engineer, I want the system to defer to me when uncertain so it doesn't make dangerous decisions.

**Acceptance Criteria**:
- System defers when confidence < 75%
- System respects rate limits (max 10 actions/hour)
- System blocks duplicate actions (idempotency)

---

### Secondary Persona: Engineering Manager

**Story 4: Audit Trail**
> As an engineering manager, I want to audit past decisions so I can understand what the system did and why.

**Acceptance Criteria**:
- Every decision logged with: event, recommendation, critique, final action
- Can query by time range, action type, blocked status
- Logs include model version, prompt version for reproducibility

---

## Project Phases

### Phase 1: Foundation (v1.0) — 30 hours
- Project structure, data models, database
- Core agents (classify, decide, critique)
- Safety layer (rate limits, confidence gates)
- Security layer (input sanitization, output validation)
- Basic RAG with Pinecone
- Evaluation framework (200 events)
- CLI interface

**Deliverable**: Working system with plain Python orchestration

---

### Phase 2: Enhanced (v2.0) — 12 hours
- LangGraph migration
- Conditional routing (severity-based)
- Parallel critics (safety + accuracy)
- Human-in-the-loop with state persistence
- Migration documentation

**Deliverable**: Production-ready orchestration with advanced features

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM API rate limits | Medium | High | Exponential backoff, fallback to human review |
| Confidence miscalibration | High | High | Calibration testing on held-out set |
| Prompt injection success | Low | Critical | Multi-layer validation, adversarial testing |
| Cloud cost overrun | Low | Medium | Aurora/Redis scale-to-zero, monitoring |
| Evaluation dataset too small | Medium | Medium | Expand to 200+ events, diverse categories |

---

## Timeline

| Week | Focus | Deliverables |
|------|-------|--------------|
| **Week 1** | Infrastructure + Foundation | Aurora, Redis, Pinecone setup; Data models |
| **Week 2** | Core Agents | Classification, Decision, Critique agents working |
| **Week 3** | Safety + Security | Rate limiting, validation, idempotency |
| **Week 4** | RAG + Evaluation | Pinecone integration, 200 labeled events, metrics |
| **Week 5** | v2 Migration | LangGraph, conditional routing, HITL |
| **Week 6** | Polish + Documentation | README, architecture diagrams, evaluation report |

**Total**: 6 weeks part-time (~45 hours total)

---

## Success Criteria (Project-Level)

### Technical Success
- [ ] All 4 tables created in Aurora with proper relationships
- [ ] All 3 agents working with structured outputs
- [ ] Safety layer blocks unsafe actions (tested)
- [ ] Evaluation shows ≥75% correct decision rate
- [ ] Confidence calibration ECE < 0.15
- [ ] v1 → v2 migration documented with trade-offs

### Portfolio Success
- [ ] GitHub repo with clear README
- [ ] Architecture diagrams (Mermaid or draw.io)
- [ ] Evaluation report with metrics and analysis
- [ ] Demo video (5 minutes)
- [ ] Can explain any design decision in interviews

### Hiring Signal Success
- [ ] Demonstrates production AI thinking (not just demos)
- [ ] Shows constraint-first design
- [ ] Proves understanding of safety vs automation trade-offs
- [ ] Signals Staff-level architectural maturity

---

## What This Project Proves

To hiring managers, this project demonstrates:

1. **You understand agentic AI without hype**
   - Not "let the agent figure it out"
   - Bounded, predictable, auditable

2. **You know where AI should NOT be trusted**
   - LLM as untrusted component
   - System enforces safety, not prompts

3. **You can design production-safe systems**
   - Rate limiting, idempotency, validation
   - Fail safe, not fail silent

4. **You think in risk, not demos**
   - Confidence calibration
   - Adversarial testing
   - Explicit abstention

5. **You can ship with modern cloud stack**
   - Aurora, Redis, Pinecone
   - Not "works on my machine"

---

## Frequently Asked Questions

### Why not just use LangChain?
LangChain is a prototyping tool. This project demonstrates production thinking: explicit control flow, type safety, and safety constraints that can't be bypassed.

### Why three agents instead of one?
Separation of concerns, testability, and different temperatures for diversity. A single mega-prompt is harder to debug and test.

### Why Aurora Serverless over RDS?
Scale-to-zero saves cost when not in use. Shows understanding of modern cloud patterns.

### Why not build a UI?
This is a portfolio project for backend/AI roles. A CLI is sufficient to demonstrate the system. UI would be scope creep.

### How is this different from AutoGPT?
AutoGPT loops until success/failure. This system has bounded execution, no loops, and explicit human-in-the-loop. Production-safe vs impressive demo.

---

## Next Steps

1. **Review this document** — Ensure alignment on scope and goals
2. **Set up infrastructure** — Aurora, Redis, Pinecone
3. **Begin Phase 1** — Foundation and core agents
4. **Iterate based on evaluation** — Metrics drive improvements

---

**Document Owner**: [Your Name]  
**Last Updated**: January 2026  
**Status**: Planning → Implementation
