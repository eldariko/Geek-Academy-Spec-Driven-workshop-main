"""In-memory refund action service."""

from __future__ import annotations

from app.models.domain import RefundEvent
from app.services.customer_store import CustomerStore
from app.services.validators import ValidationError, require_non_empty, validate_amount


class RefundService:
    """Records approved refund events and appends them to customer history."""

    def __init__(self, store: CustomerStore | None = None) -> None:
        self.store = store or CustomerStore()

    def record_refund_event(self, customer_id: object, amount: object, reason: object) -> RefundEvent:
        normalized_customer_id = require_non_empty(customer_id, "customer_id")
        normalized_reason = require_non_empty(reason, "reason")
        normalized_amount = validate_amount(amount)

        if not self.store.exists_customer_id(normalized_customer_id):
            raise ValidationError("CUSTOMER_NOT_FOUND", "Customer record was not found")

        return self.store.append_refund_event(
            customer_id=normalized_customer_id,
            amount=normalized_amount,
            reason=normalized_reason,
        )
