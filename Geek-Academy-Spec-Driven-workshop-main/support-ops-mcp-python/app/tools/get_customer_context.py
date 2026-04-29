"""MCP tool handler for fetching customer context by email."""

from dataclasses import asdict

from app.models.results import ActionResult
from app.services.customer_store import CustomerStore
from app.services.error_mapper import make_error
from app.services.validators import ValidationError, normalize_email


def get_customer_context(email: str, store: CustomerStore | None = None) -> dict:
    customer_store = store or CustomerStore()

    try:
        normalized_email = normalize_email(email)
    except ValidationError as exc:
        return make_error(exc.code, exc.message).to_dict()

    try:
        customer = customer_store.get_by_email(normalized_email)
        if customer is None:
            return make_error("CUSTOMER_NOT_FOUND", "No customer found for the supplied email").to_dict()

        result = ActionResult(ok=True, payload={"customer": asdict(customer)})
        return result.to_dict()
    except Exception:
        return make_error("INTERNAL_ERROR").to_dict()
