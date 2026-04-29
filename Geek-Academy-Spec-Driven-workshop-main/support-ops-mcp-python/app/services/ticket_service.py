"""In-memory ticket action service."""

from __future__ import annotations

from app.models.domain import SupportTicket, utc_now_iso
from app.services.customer_store import CustomerStore
from app.services.validators import ValidationError, require_non_empty, validate_priority


class TicketService:
    """Creates escalation tickets after validating action contract inputs."""

    def __init__(self, store: CustomerStore | None = None) -> None:
        self.store = store or CustomerStore()
        self._tickets: list[SupportTicket] = []

    def create_ticket(self, customer_id: object, reason: object, priority: object) -> SupportTicket:
        normalized_customer_id = require_non_empty(customer_id, "customer_id")
        normalized_reason = require_non_empty(reason, "reason")
        normalized_priority = validate_priority(priority)

        if not self.store.exists_customer_id(normalized_customer_id):
            raise ValidationError("CUSTOMER_NOT_FOUND", "Customer record was not found")

        ticket = SupportTicket(
            ticket_id=f"tkt_{len(self._tickets) + 1:04d}",
            customer_id=normalized_customer_id,
            reason=normalized_reason,
            priority=normalized_priority,
            status="open",
            created_at=utc_now_iso(),
        )
        self._tickets.append(ticket)
        return ticket
