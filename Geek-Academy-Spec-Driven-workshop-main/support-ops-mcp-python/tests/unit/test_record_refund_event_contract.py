from app.services.customer_store import CustomerStore
from app.services.refund_service import RefundService
from app.tools.get_customer_context import get_customer_context
from app.tools.record_refund_event import record_refund_event


def test_record_refund_event_success_shape() -> None:
    store = CustomerStore()
    service = RefundService(store=store)

    result = record_refund_event(
        customer_id="cust_0001",
        amount=19.99,
        reason="service_issue",
        refund_service=service,
    )

    assert result["ok"] is True
    assert "refund_event" in result
    assert result["refund_event"]["customer_id"] == "cust_0001"
    assert result["refund_event"]["amount"] == 19.99


def test_record_refund_event_invalid_amount() -> None:
    store = CustomerStore()
    service = RefundService(store=store)

    result = record_refund_event(
        customer_id="cust_0001",
        amount=0,
        reason="billing_error",
        refund_service=service,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_AMOUNT"


def test_record_refund_event_unknown_customer() -> None:
    store = CustomerStore()
    service = RefundService(store=store)

    result = record_refund_event(
        customer_id="cust_9999",
        amount=9.99,
        reason="billing_error",
        refund_service=service,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "CUSTOMER_NOT_FOUND"


def test_record_refund_event_visible_in_subsequent_customer_context() -> None:
    store = CustomerStore()
    service = RefundService(store=store)

    create_result = record_refund_event(
        customer_id="cust_0001",
        amount=29.99,
        reason="goodwill",
        refund_service=service,
    )
    assert create_result["ok"] is True

    context_result = get_customer_context("alice@example.com", store=store)
    assert context_result["ok"] is True
    assert len(context_result["customer"]["refund_history"]) == 1
    assert context_result["customer"]["refund_history"][0]["amount"] == 29.99
