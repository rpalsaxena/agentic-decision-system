"""
Pydantic models for data validation and serialization.

These models define the shape of data flowing through the system:
- Events from external systems
- Decisions from AI agents
- Critiques from safety reviewer
- Audit logs for compliance
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum


class Severity(str, Enum):
    """Event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Verdict(str, Enum):
    """Critic verdict options"""
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"


class Event(BaseModel):
    """
    Raw operational event from external systems.
    
    Examples:
    - PagerDuty alert
    - CloudWatch alarm
    - Security incident
    - Application error
    """
    id: Optional[UUID] = None
    timestamp: datetime
    source: str = Field(..., description="System that generated the event")
    raw_payload: Dict[str, Any] = Field(..., description="Original event data")
    event_type: Optional[str] = Field(None, description="Classified event type")
    severity: Optional[Severity] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-01-06T10:30:00Z",
                "source": "cloudwatch",
                "raw_payload": {
                    "alert_name": "HighCPUUsage",
                    "service": "api-server",
                    "value": 95.2
                },
                "event_type": "performance",
                "severity": "high"
            }
        }


class Decision(BaseModel):
    """
    AI agent's recommended action for an event.
    
    Includes reasoning and confidence score for auditability.
    """
    id: Optional[UUID] = None
    event_id: UUID
    agent_type: str = Field(..., description="Which agent made this decision")
    action: str = Field(..., description="Recommended action to take")
    reasoning: Optional[str] = Field(None, description="Explanation of why this action")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1"""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0 and 1')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "123e4567-e89b-12d3-a456-426614174000",
                "agent_type": "decision_agent",
                "action": "scale_up_instances",
                "reasoning": "CPU usage at 95% for 10+ minutes. Recommend scaling.",
                "confidence": 0.87
            }
        }


class Critique(BaseModel):
    """
    Safety reviewer's evaluation of a decision.
    
    Acts as adversarial check on the decision agent.
    """
    id: Optional[UUID] = None
    decision_id: UUID
    verdict: Verdict = Field(..., description="approve/reject/defer")
    risk_flags: List[str] = Field(default_factory=list, description="Identified risks")
    reasoning: Optional[str] = Field(None, description="Why this verdict")
    confidence: float = Field(..., ge=0.0, le=1.0)
    created_at: Optional[datetime] = None
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1"""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0 and 1')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "decision_id": "223e4567-e89b-12d3-a456-426614174000",
                "verdict": "approve",
                "risk_flags": [],
                "reasoning": "Action is appropriate. No safety concerns identified.",
                "confidence": 0.92
            }
        }


class AuditLog(BaseModel):
    """
    Complete audit trail for compliance and debugging.
    
    Links event → decision → critique → final action.
    """
    id: Optional[UUID] = None
    event_id: UUID
    decision_id: UUID
    critique_id: UUID
    event_hash: str = Field(..., description="SHA256 hash for idempotency")
    final_action: str = Field(..., description="Action that was taken")
    blocked: bool = Field(default=False, description="Was action blocked?")
    block_reason: Optional[str] = None
    latency_ms: Optional[int] = Field(None, description="Processing time in ms")
    safety_checks: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "123e4567-e89b-12d3-a456-426614174000",
                "decision_id": "223e4567-e89b-12d3-a456-426614174000",
                "critique_id": "323e4567-e89b-12d3-a456-426614174000",
                "event_hash": "abc123def456...",
                "final_action": "scale_up_instances",
                "blocked": False,
                "latency_ms": 1250,
                "safety_checks": {
                    "rate_limit": "passed",
                    "confidence_threshold": "passed"
                }
            }
        }


# LLM Agent Output Models (for Instructor)

class DecisionOutput(BaseModel):
    """
    Structured output from Decision Agent.
    
    Used with Instructor for type-safe LLM responses.
    """
    action: str = Field(..., description="Recommended action")
    reasoning: str = Field(..., description="Explanation of recommendation")
    confidence: float = Field(..., ge=0.0, le=1.0)
    alternative_actions: List[str] = Field(
        default_factory=list,
        description="Other actions considered"
    )


class CritiqueOutput(BaseModel):
    """
    Structured output from Critic Agent.
    
    Used with Instructor for type-safe LLM responses.
    """
    verdict: Verdict
    risk_flags: List[str] = Field(default_factory=list)
    reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)
