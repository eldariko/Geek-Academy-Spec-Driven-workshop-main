from app.services.validators import (
    ValidationError,
    normalize_email,
    require_non_empty,
    validate_amount,
    validate_plan_type,
    validate_priority,
)


def test_normalize_email_lowercases_and_trims() -> None:
    assert normalize_email("  Alice@Example.COM  ") == "alice@example.com"


def test_normalize_email_rejects_empty() -> None:
    try:
        normalize_email("   ")
        assert False, "Expected ValidationError"
    except ValidationError as exc:
        assert exc.code == "INVALID_ARGUMENT"


def test_validate_plan_type_allows_contract_values_only() -> None:
    assert validate_plan_type("Basic") == "Basic"
    assert validate_plan_type("Premium") == "Premium"

    try:
        validate_plan_type("basic")
        assert False, "Expected ValidationError"
    except ValidationError as exc:
        assert exc.code == "INVALID_ARGUMENT"


def test_validate_priority_accepts_known_values() -> None:
    assert validate_priority("low") == "low"
    assert validate_priority("medium") == "medium"
    assert validate_priority("high") == "high"
    assert validate_priority("urgent") == "urgent"


def test_validate_priority_rejects_unknown_value() -> None:
    try:
        validate_priority("critical")
        assert False, "Expected ValidationError"
    except ValidationError as exc:
        assert exc.code == "INVALID_PRIORITY"


def test_validate_amount_must_be_positive() -> None:
    assert validate_amount(1) == 1.0
    assert validate_amount("3.50") == 3.5

    for value in (0, -1, "abc"):
        try:
            validate_amount(value)
            assert False, "Expected ValidationError"
        except ValidationError as exc:
            assert exc.code == "INVALID_AMOUNT"


def test_require_non_empty_enforces_required_non_blank() -> None:
    assert require_non_empty(" value ", "reason") == "value"

    for value in (None, "  "):
        try:
            require_non_empty(value, "reason")
            assert False, "Expected ValidationError"
        except ValidationError as exc:
            assert exc.code == "INVALID_ARGUMENT"
