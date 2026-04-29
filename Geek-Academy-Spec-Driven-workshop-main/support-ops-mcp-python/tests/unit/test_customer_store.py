import json

from app.services.customer_store import CustomerStore


def test_customer_store_loads_mock_data() -> None:
    store = CustomerStore()
    customer = store.get_by_email("alice@example.com")
    assert customer is not None
    assert customer.email == "alice@example.com"
    assert customer.plan_type in {"Basic", "Premium"}


def test_customer_store_email_lookup_is_case_insensitive() -> None:
    store = CustomerStore()
    customer = store.get_by_email("Alice@Example.com")
    assert customer is not None
    assert customer.email == "alice@example.com"


def test_customer_store_rejects_invalid_plan(tmp_path) -> None:
    payload = [
        {
            "customer_email": "x@example.com",
            "customer_name": "X",
            "plan": "Enterprise",
            "refunds_last_12_months": 0,
        }
    ]
    file_path = tmp_path / "customers.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")

    try:
        CustomerStore(file_path)
        assert False, "Expected ValueError"
    except Exception as exc:
        assert "plan_type" in str(exc)
