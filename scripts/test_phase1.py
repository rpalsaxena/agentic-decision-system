"""
Test Phase 1 Foundation - Database, Cache, and Models

Tests all foundational components:
- Pydantic models validation
- Database operations (asyncpg)
- Redis cache operations
- Complete event → decision → critique → audit workflow
"""

import asyncio
from datetime import datetime
from dotenv import load_dotenv
import sys
import os
import hashlib
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.db.operations import db
from src.cache.manager import cache
from src.models.schemas import (
    Event, Decision, Critique, AuditLog,
    Severity, Verdict
)

load_dotenv()


async def test_models():
    """Test Pydantic model validation"""
    print("\n🧪 Testing Pydantic Models...")
    
    # Test Event model
    event = Event(
        timestamp=datetime.now(),
        source="test_system",
        raw_payload={"alert": "HighCPU", "value": 95},
        event_type="performance",
        severity=Severity.HIGH
    )
    assert event.severity == Severity.HIGH
    print("  ✅ Event model validated")
    
    # Test Decision model with confidence validation
    try:
        invalid_decision = Decision(
            event_id=event.id,
            agent_type="test",
            action="test",
            reasoning="test",
            confidence=1.5  # Invalid!
        )
        print("  ❌ Should have raised validation error")
    except ValueError:
        print("  ✅ Decision confidence validation working")
    
    # Test valid decision
    decision = Decision(
        event_id=event.id or "00000000-0000-0000-0000-000000000000",
        agent_type="decision_agent",
        action="scale_up",
        reasoning="CPU at 95%",
        confidence=0.87
    )
    assert 0 <= decision.confidence <= 1
    print("  ✅ Decision model validated")
    
    # Test Critique model
    critique = Critique(
        decision_id=decision.id or "00000000-0000-0000-0000-000000000000",
        verdict=Verdict.APPROVE,
        risk_flags=[],
        reasoning="Action is safe",
        confidence=0.92
    )
    assert critique.verdict == Verdict.APPROVE
    print("  ✅ Critique model validated")


async def test_database():
    """Test database operations"""
    print("\n🧪 Testing Database Operations...")
    
    await db.connect()
    
    try:
        # 1. Insert Event
        event = Event(
            timestamp=datetime.now(),
            source="test_phase1",
            raw_payload={"action": "login", "user": "test@example.com"},
            event_type="authentication",
            severity=Severity.MEDIUM
        )
        event_id = await db.insert_event(event)
        print(f"  ✅ Event created: {event_id}")
        
        # 2. Fetch Event
        fetched_event = await db.get_event(event_id)
        assert fetched_event.source == "test_phase1"
        print(f"  ✅ Event fetched: {fetched_event.source}")
        
        # 3. Insert Decision
        decision = Decision(
            event_id=event_id,
            agent_type="auth_agent",
            action="allow_login",
            reasoning="Valid credentials, no fraud flags",
            confidence=0.95
        )
        decision_id = await db.insert_decision(decision)
        print(f"  ✅ Decision created: {decision_id}")
        
        # 4. Insert Critique
        critique = Critique(
            decision_id=decision_id,
            verdict=Verdict.APPROVE,
            risk_flags=[],
            reasoning="No security concerns detected",
            confidence=0.93
        )
        critique_id = await db.insert_critique(critique)
        print(f"  ✅ Critique created: {critique_id}")
        
        # 5. Create event hash for idempotency
        event_data = {
            "source": event.source,
            "timestamp": event.timestamp.isoformat(),
            "payload": event.raw_payload
        }
        event_hash = hashlib.sha256(
            json.dumps(event_data, sort_keys=True).encode()
        ).hexdigest()
        
        # 6. Insert Audit Log
        audit = AuditLog(
            event_id=event_id,
            decision_id=decision_id,
            critique_id=critique_id,
            event_hash=event_hash,
            final_action="allow_login",
            blocked=False,
            latency_ms=234,
            safety_checks={
                "rate_limit": "passed",
                "confidence": "passed",
                "idempotency": "passed"
            }
        )
        audit_id = await db.insert_audit_log(audit)
        print(f"  ✅ Audit log created: {audit_id}")
        
        # 7. Query operations
        recent_events = await db.get_recent_events(limit=5)
        print(f"  ✅ Fetched {len(recent_events)} recent events")
        
        decisions_for_event = await db.get_decisions_for_event(event_id)
        print(f"  ✅ Fetched {len(decisions_for_event)} decisions for event")
        
        audit_logs = await db.get_audit_logs(limit=10)
        print(f"  ✅ Fetched {len(audit_logs)} audit logs")
        
        # 8. Check idempotency
        already_processed = await db.check_event_processed(event_hash)
        assert already_processed == True
        print(f"  ✅ Idempotency check working")
        
    finally:
        await db.close()


async def test_cache():
    """Test Redis cache operations"""
    print("\n🧪 Testing Redis Cache Operations...")
    
    await cache.connect()
    
    try:
        # 1. Basic set/get
        await cache.set("test_key", "test_value", ttl_seconds=60)
        value = await cache.get("test_key")
        assert value == "test_value"
        print("  ✅ Basic set/get working")
        
        # 2. Rate limiting
        allowed, count = await cache.check_rate_limit(
            "test_action",
            max_requests=10,
            window_seconds=60
        )
        assert allowed == True
        assert count == 1
        print(f"  ✅ Rate limiting working (count: {count})")
        
        # Make 9 more requests
        for _ in range(9):
            allowed, count = await cache.check_rate_limit(
                "test_action",
                max_requests=10,
                window_seconds=60
            )
        
        assert count == 10
        print(f"  ✅ Rate limit at threshold (count: {count})")
        
        # Try one more (should be blocked)
        allowed, count = await cache.check_rate_limit(
            "test_action",
            max_requests=10,
            window_seconds=60
        )
        assert allowed == False
        assert count == 11
        print(f"  ✅ Rate limit exceeded correctly (count: {count}, allowed: {allowed})")
        
        # Reset and verify
        await cache.reset_rate_limit("test_action")
        allowed, count = await cache.check_rate_limit(
            "test_action",
            max_requests=10,
            window_seconds=60
        )
        assert count == 1
        print(f"  ✅ Rate limit reset working")
        
        # 3. Idempotency check
        test_hash = "test_event_hash_12345"
        
        is_duplicate = await cache.check_idempotency(test_hash, ttl_seconds=60)
        assert is_duplicate == False  # First time
        print(f"  ✅ First event detected as new")
        
        is_duplicate = await cache.check_idempotency(test_hash, ttl_seconds=60)
        assert is_duplicate == True  # Duplicate
        print(f"  ✅ Duplicate event detected")
        
        # 4. Get cache info
        info = await cache.get_info()
        print(f"  ✅ Redis info: {info['version']}, {info['connected_clients']} clients")
        
        # Cleanup
        await cache.delete("test_key")
        await cache.reset_rate_limit("test_action")
        
    finally:
        await cache.close()


async def test_complete_workflow():
    """Test complete event processing workflow"""
    print("\n🧪 Testing Complete Workflow...")
    
    await db.connect()
    await cache.connect()
    
    try:
        # Simulate event arrival
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "source": "cloudwatch",
            "payload": {"alert": "HighMemory", "value": 89}
        }
        
        # 1. Check idempotency
        event_hash = hashlib.sha256(
            json.dumps(event_data, sort_keys=True).encode()
        ).hexdigest()
        
        is_duplicate = await cache.check_idempotency(event_hash)
        if is_duplicate:
            print("  ⚠️  Duplicate event (would skip)")
            return
        print("  ✅ New event (processing)")
        
        # 2. Check rate limit
        allowed, count = await cache.check_rate_limit(
            "actions_per_hour",
            max_requests=10
        )
        if not allowed:
            print(f"  ⚠️  Rate limit exceeded ({count} requests)")
            return
        print(f"  ✅ Rate limit check passed ({count}/10)")
        
        # 3. Store event
        event = Event(
            timestamp=datetime.now(),
            source="cloudwatch",
            raw_payload=event_data["payload"],
            event_type="performance",
            severity=Severity.HIGH
        )
        event_id = await db.insert_event(event)
        print(f"  ✅ Event stored: {event_id}")
        
        # 4. Make decision (simulated)
        decision = Decision(
            event_id=event_id,
            agent_type="performance_agent",
            action="increase_memory_limit",
            reasoning="Memory at 89%, trending up",
            confidence=0.88
        )
        decision_id = await db.insert_decision(decision)
        print(f"  ✅ Decision made: {decision.action}")
        
        # 5. Critique decision (simulated)
        critique = Critique(
            decision_id=decision_id,
            verdict=Verdict.APPROVE,
            risk_flags=[],
            reasoning="Safe action, no risks identified",
            confidence=0.91
        )
        critique_id = await db.insert_critique(critique)
        print(f"  ✅ Critique: {critique.verdict.value}")
        
        # 6. Create audit log
        audit = AuditLog(
            event_id=event_id,
            decision_id=decision_id,
            critique_id=critique_id,
            event_hash=event_hash,
            final_action="increase_memory_limit",
            blocked=False,
            latency_ms=456,
            safety_checks={
                "idempotency": "passed",
                "rate_limit": "passed",
                "confidence": "passed"
            }
        )
        audit_id = await db.insert_audit_log(audit)
        print(f"  ✅ Audit log created")
        
        print("\n  ✅ Complete workflow successful!")
        
    finally:
        await cache.reset_rate_limit("actions_per_hour")
        await db.close()
        await cache.close()


async def main():
    print("=" * 60)
    print("  Phase 1 Foundation Test Suite")
    print("=" * 60)
    
    await test_models()
    await test_database()
    await test_cache()
    await test_complete_workflow()
    
    print("\n" + "=" * 60)
    print("  ✅ All Phase 1 tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
