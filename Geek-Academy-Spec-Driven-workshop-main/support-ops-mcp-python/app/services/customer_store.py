"""Customer context store backed by mock customer JSON."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import DEFAULT_CUSTOMER_DATA_PATH
from app.models.domain import CustomerContext, RefundEvent, RefundHistoryItem, utc_now_iso
from app.services.validators import normalize_email, validate_plan_type


class CustomerStore:
    """Read-only customer profile store with deterministic customer IDs."""

    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or DEFAULT_CUSTOMER_DATA_PATH
        self._customers_by_email: dict[str, CustomerContext] = {}
        self._customers_by_id: dict[str, CustomerContext] = {}
        self._load()

    def _load(self) -> None:
        data = json.loads(self.data_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("Customer store payload must be a list")

        loaded: dict[str, CustomerContext] = {}
        for idx, raw in enumerate(data, start=1):
            if not isinstance(raw, dict):
                raise ValueError("Each customer entry must be an object")

            email = normalize_email(raw.get("customer_email"))
            name = str(raw.get("customer_name", "")).strip()
            if not name:
                raise ValueError("customer_name is required")

            plan_type = validate_plan_type(raw.get("plan"))
            refund_count = int(raw.get("refunds_last_12_months", 0))
            if refund_count < 0:
                raise ValueError("refunds_last_12_months cannot be negative")

            # Mock dataset does not include explicit refund event history, so start empty.
            customer = CustomerContext(
                customer_id=f"cust_{idx:04d}",
                email=email,
                name=name,
                plan_type=plan_type,
                refund_history=[],
            )
            loaded[email] = customer

        self._customers_by_email = loaded
        self._customers_by_id = {customer.customer_id: customer for customer in loaded.values()}

    def get_by_email(self, email: str) -> CustomerContext | None:
        return self._customers_by_email.get(normalize_email(email))

    def exists_customer_id(self, customer_id: str) -> bool:
        return customer_id in self._customers_by_id

    def get_by_customer_id(self, customer_id: str) -> CustomerContext | None:
        return self._customers_by_id.get(customer_id)

    def append_refund_event(self, customer_id: str, amount: float, reason: str) -> RefundEvent:
        customer = self.get_by_customer_id(customer_id)
        if customer is None:
            raise ValueError("customer_id not found")

        event_id = f"ref_{sum(len(c.refund_history) for c in self._customers_by_email.values()) + 1:04d}"
        created_at = utc_now_iso()
        history_item = RefundHistoryItem(
            event_id=event_id,
            amount=amount,
            reason=reason,
            occurred_at=created_at,
        )
        customer.refund_history.append(history_item)

        return RefundEvent(
            event_id=event_id,
            customer_id=customer_id,
            amount=amount,
            reason=reason,
            created_at=created_at,
        )
