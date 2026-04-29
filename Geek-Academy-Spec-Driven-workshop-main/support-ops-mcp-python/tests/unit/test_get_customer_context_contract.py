from app.tools.get_customer_context import get_customer_context


def test_get_customer_context_success_shape() -> None:
    result = get_customer_context("alice@example.com")

    assert result["ok"] is True
    assert "customer" in result
    customer = result["customer"]
    assert customer["email"] == "alice@example.com"
    assert customer["plan_type"] in {"Basic", "Premium"}
    assert "refund_history" in customer


def test_get_customer_context_normalizes_email() -> None:
    result = get_customer_context("  Alice@Example.COM ")

    assert result["ok"] is True
    assert result["customer"]["email"] == "alice@example.com"


def test_get_customer_context_unknown_customer() -> None:
    result = get_customer_context("missing@example.com")

    assert result == {
        "ok": False,
        "error": {
            "code": "CUSTOMER_NOT_FOUND",
            "message": "No customer found for the supplied email",
        },
    }


def test_get_customer_context_invalid_argument() -> None:
    result = get_customer_context("   ")

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_ARGUMENT"
