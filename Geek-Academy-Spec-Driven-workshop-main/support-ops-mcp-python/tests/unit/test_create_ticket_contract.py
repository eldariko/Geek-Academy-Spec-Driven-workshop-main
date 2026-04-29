from app.services.customer_store import CustomerStore
from app.services.ticket_service import TicketService
from app.tools.create_ticket import create_ticket


def test_create_ticket_success_shape() -> None:
    store = CustomerStore()
    service = TicketService(store=store)

    result = create_ticket(
        customer_id="cust_0001",
        reason="legal_threat",
        priority="high",
        ticket_service=service,
    )

    assert result["ok"] is True
    assert "ticket" in result
    assert result["ticket"]["customer_id"] == "cust_0001"
    assert result["ticket"]["priority"] == "high"
    assert result["ticket"]["status"] == "open"


def test_create_ticket_invalid_priority() -> None:
    store = CustomerStore()
    service = TicketService(store=store)

    result = create_ticket(
        customer_id="cust_0001",
        reason="needs_manual_review",
        priority="critical",
        ticket_service=service,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_PRIORITY"


def test_create_ticket_missing_reason() -> None:
    store = CustomerStore()
    service = TicketService(store=store)

    result = create_ticket(
        customer_id="cust_0001",
        reason="   ",
        priority="low",
        ticket_service=service,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_ARGUMENT"


def test_create_ticket_unknown_customer() -> None:
    store = CustomerStore()
    service = TicketService(store=store)

    result = create_ticket(
        customer_id="cust_9999",
        reason="escalation_requested",
        priority="medium",
        ticket_service=service,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "CUSTOMER_NOT_FOUND"
