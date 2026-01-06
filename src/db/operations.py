"""
Database operations layer using asyncpg.

Provides connection pooling and CRUD operations for all tables.
Uses raw SQL for performance and explicitness.
"""

import asyncpg
import os
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import json

from ..models.schemas import Event, Decision, Critique, AuditLog


class DatabaseManager:
    """
    Manages PostgreSQL connection pool and database operations.
    
    Features:
    - Connection pooling for performance
    - Async-native operations
    - Transaction support
    - Type-safe with Pydantic models
    """
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self, database_url: Optional[str] = None):
        """
        Create connection pool to PostgreSQL.
        
        Args:
            database_url: Connection string. Falls back to DATABASE_URL env var.
        """
        url = database_url or os.getenv('DATABASE_URL')
        if not url:
            raise ValueError("DATABASE_URL not set")
        
        self.pool = await asyncpg.create_pool(
            url,
            min_size=2,  # Keep 2 connections warm
            max_size=10,  # Max 10 concurrent connections
            command_timeout=60
        )
    
    async def close(self):
        """Close connection pool gracefully"""
        if self.pool:
            await self.pool.close()
    
    # ========================================
    # EVENT OPERATIONS
    # ========================================
    
    async def insert_event(self, event: Event) -> UUID:
        """
        Insert a new event into the database.
        
        Args:
            event: Event model to insert
            
        Returns:
            UUID of created event
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO events (timestamp, source, raw_payload, event_type, severity)
                VALUES ($1, $2, $3::jsonb, $4, $5)
                RETURNING id
            """, 
                event.timestamp,
                event.source,
                json.dumps(event.raw_payload),
                event.event_type,
                event.severity.value if event.severity else None
            )
            return row['id']
    
    async def get_event(self, event_id: UUID) -> Optional[Event]:
        """Fetch event by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM events WHERE id = $1",
                event_id
            )
            if not row:
                return None
            
            return Event(
                id=row['id'],
                timestamp=row['timestamp'],
                source=row['source'],
                raw_payload=json.loads(row['raw_payload']) if isinstance(row['raw_payload'], str) else row['raw_payload'],
                event_type=row['event_type'],
                severity=row['severity'],
                created_at=row['created_at']
            )
    
    async def get_recent_events(self, limit: int = 100) -> List[Event]:
        """Fetch recent events ordered by timestamp"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT $1",
                limit
            )
            
            return [
                Event(
                    id=row['id'],
                    timestamp=row['timestamp'],
                    source=row['source'],
                    raw_payload=json.loads(row['raw_payload']) if isinstance(row['raw_payload'], str) else row['raw_payload'],
                    event_type=row['event_type'],
                    severity=row['severity'],
                    created_at=row['created_at']
                )
                for row in rows
            ]
    
    # ========================================
    # DECISION OPERATIONS
    # ========================================
    
    async def insert_decision(self, decision: Decision) -> UUID:
        """Insert agent decision"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO decisions 
                (event_id, agent_type, action, reasoning, confidence, metadata)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                RETURNING id
            """,
                decision.event_id,
                decision.agent_type,
                decision.action,
                decision.reasoning,
                decision.confidence,
                json.dumps(decision.metadata)
            )
            return row['id']
    
    async def get_decision(self, decision_id: UUID) -> Optional[Decision]:
        """Fetch decision by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM decisions WHERE id = $1",
                decision_id
            )
            if not row:
                return None
            
            return Decision(
                id=row['id'],
                event_id=row['event_id'],
                agent_type=row['agent_type'],
                action=row['action'],
                reasoning=row['reasoning'],
                confidence=row['confidence'],
                metadata=json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata'],
                created_at=row['created_at']
            )
    
    async def get_decisions_for_event(self, event_id: UUID) -> List[Decision]:
        """Get all decisions for a specific event"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM decisions WHERE event_id = $1 ORDER BY created_at",
                event_id
            )
            
            return [
                Decision(
                    id=row['id'],
                    event_id=row['event_id'],
                    agent_type=row['agent_type'],
                    action=row['action'],
                    reasoning=row['reasoning'],
                    confidence=row['confidence'],
                    metadata=json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata'],
                    created_at=row['created_at']
                )
                for row in rows
            ]
    
    # ========================================
    # CRITIQUE OPERATIONS
    # ========================================
    
    async def insert_critique(self, critique: Critique) -> UUID:
        """Insert critic evaluation"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO critiques 
                (decision_id, verdict, risk_flags, reasoning, confidence)
                VALUES ($1, $2, $3::jsonb, $4, $5)
                RETURNING id
            """,
                critique.decision_id,
                critique.verdict.value,
                json.dumps(critique.risk_flags),
                critique.reasoning,
                critique.confidence
            )
            return row['id']
    
    async def get_critique(self, critique_id: UUID) -> Optional[Critique]:
        """Fetch critique by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM critiques WHERE id = $1",
                critique_id
            )
            if not row:
                return None
            
            return Critique(
                id=row['id'],
                decision_id=row['decision_id'],
                verdict=row['verdict'],
                risk_flags=json.loads(row['risk_flags']) if isinstance(row['risk_flags'], str) else row['risk_flags'],
                reasoning=row['reasoning'],
                confidence=row['confidence'],
                created_at=row['created_at']
            )
    
    # ========================================
    # AUDIT LOG OPERATIONS
    # ========================================
    
    async def insert_audit_log(self, audit: AuditLog) -> UUID:
        """Insert audit log entry"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO audit_logs 
                (event_id, decision_id, critique_id, event_hash, final_action,
                 blocked, block_reason, latency_ms, safety_checks)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
                RETURNING id
            """,
                audit.event_id,
                audit.decision_id,
                audit.critique_id,
                audit.event_hash,
                audit.final_action,
                audit.blocked,
                audit.block_reason,
                audit.latency_ms,
                json.dumps(audit.safety_checks)
            )
            return row['id']
    
    async def get_audit_logs(
        self,
        limit: int = 100,
        blocked_only: bool = False
    ) -> List[AuditLog]:
        """
        Fetch audit logs with optional filtering.
        
        Args:
            limit: Maximum number of logs to return
            blocked_only: If True, only return blocked actions
        """
        async with self.pool.acquire() as conn:
            if blocked_only:
                query = """
                    SELECT * FROM audit_logs 
                    WHERE blocked = TRUE 
                    ORDER BY created_at DESC 
                    LIMIT $1
                """
            else:
                query = """
                    SELECT * FROM audit_logs 
                    ORDER BY created_at DESC 
                    LIMIT $1
                """
            
            rows = await conn.fetch(query, limit)
            
            return [
                AuditLog(
                    id=row['id'],
                    event_id=row['event_id'],
                    decision_id=row['decision_id'],
                    critique_id=row['critique_id'],
                    event_hash=row['event_hash'],
                    final_action=row['final_action'],
                    blocked=row['blocked'],
                    block_reason=row['block_reason'],
                    latency_ms=row['latency_ms'],
                    safety_checks=json.loads(row['safety_checks']) if isinstance(row['safety_checks'], str) else row['safety_checks'],
                    created_at=row['created_at']
                )
                for row in rows
            ]
    
    async def check_event_processed(self, event_hash: str) -> bool:
        """
        Check if event with this hash was already processed.
        
        Used for idempotency checks.
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM audit_logs WHERE event_hash = $1",
                event_hash
            )
            return result > 0


# Global database instance
db = DatabaseManager()
