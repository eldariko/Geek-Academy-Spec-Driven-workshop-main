"""Contract-first validation helpers used by MCP tools."""

from dataclasses import dataclass

ALLOWED_PLAN_TYPES = {"Basic", "Premium"}
ALLOWED_PRIORITIES = {"low", "medium", "high", "urgent"}


@dataclass(slots=True)
class ValidationError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


def require_non_empty(value: object, field_name: str) -> str:
    if value is None:
        raise ValidationError("INVALID_ARGUMENT", f"{field_name} is required")
    if not isinstance(value, str):
        raise ValidationError("INVALID_ARGUMENT", f"{field_name} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError("INVALID_ARGUMENT", f"{field_name} must be non-empty")
    return cleaned


def normalize_email(value: object) -> str:
    email = require_non_empty(value, "email")
    return email.lower()


def validate_plan_type(value: object) -> str:
    plan_type = require_non_empty(value, "plan_type")
    if plan_type not in ALLOWED_PLAN_TYPES:
        raise ValidationError("INVALID_ARGUMENT", "plan_type must be one of Basic|Premium")
    return plan_type


def validate_priority(value: object) -> str:
    priority = require_non_empty(value, "priority")
    if priority not in ALLOWED_PRIORITIES:
        raise ValidationError("INVALID_PRIORITY", "Priority must be one of low|medium|high|urgent")
    return priority


def validate_amount(value: object) -> float:
    if value is None:
        raise ValidationError("INVALID_ARGUMENT", "amount is required")
    try:
        amount = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("INVALID_AMOUNT", "Refund amount must be greater than zero") from exc

    if amount <= 0:
        raise ValidationError("INVALID_AMOUNT", "Refund amount must be greater than zero")
    return amount
