"""MCP tool handler for recording successful refund events."""

from dataclasses import asdict

from app.models.results import ActionResult
from app.services.error_mapper import make_error
from app.services.refund_service import RefundService
from app.services.validators import ValidationError


def record_refund_event(customer_id: str, amount: float, reason: str, refund_service: RefundService | None = None) -> dict:
    service = refund_service or RefundService()

    try:
        refund_event = service.record_refund_event(customer_id=customer_id, amount=amount, reason=reason)
        result = ActionResult(ok=True, payload={"refund_event": asdict(refund_event)})
        return result.to_dict()
    except ValidationError as exc:
        return make_error(exc.code, exc.message).to_dict()
    except Exception:
        return make_error("INTERNAL_ERROR").to_dict()
