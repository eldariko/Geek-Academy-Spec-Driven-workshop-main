"""Domain models for SupportOps MCP tools."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


PlanType = Literal["Basic", "Premium"]
TicketPriority = Literal["low", "medium", "high", "urgent"]


@dataclass(slots=True)
class RefundHistoryItem:
    event_id: str
    amount: float
    reason: str
    occurred_at: str


@dataclass(slots=True)
class CustomerContext:
    customer_id: str
    email: str
    name: str
    plan_type: PlanType
    refund_history: list[RefundHistoryItem] = field(default_factory=list)


@dataclass(slots=True)
class SupportTicket:
    ticket_id: str
    customer_id: str
    reason: str
    priority: TicketPriority
    status: str
    created_at: str


@dataclass(slots=True)
class RefundEvent:
    event_id: str
    customer_id: str
    amount: float
    reason: str
    created_at: str


def utc_now_iso() -> str:
    """Return a stable UTC ISO timestamp with trailing Z."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
