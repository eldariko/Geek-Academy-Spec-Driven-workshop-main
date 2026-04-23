"""Approval data models for Human-in-the-Loop refund approval"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional


@dataclass
class Recommendation:
    """Agent's structured recommendation for a refund request"""

    request_id: str
    suggested_decision: Literal["approve", "reject"]
    reasoning: str
    policy_rules_applied: list[str]
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class HumanDecision:
    """Operator's recorded decision in response to a Recommendation"""

    request_id: str
    decision: Literal["approve", "reject"]
    operator_note: Optional[str]
    operator_id: str
    decided_at: datetime
    overrides_recommendation: bool


@dataclass
class AuditLogEntry:
    """Immutable audit record linking a Recommendation to a HumanDecision"""

    entry_id: str
    request_id: str
    agent_recommendation: Literal["approve", "reject"]
    agent_reasoning: str
    human_decision: Literal["approve", "reject"]
    operator_note: Optional[str]
    operator_id: str
    is_override: bool
    decided_at: datetime
