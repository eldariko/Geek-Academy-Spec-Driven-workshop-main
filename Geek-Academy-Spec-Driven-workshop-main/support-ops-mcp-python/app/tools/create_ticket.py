"""MCP tool handler for escalation ticket creation."""

from dataclasses import asdict

from app.models.results import ActionResult
from app.services.error_mapper import make_error
from app.services.ticket_service import TicketService
from app.services.validators import ValidationError


def create_ticket(customer_id: str, reason: str, priority: str, ticket_service: TicketService | None = None) -> dict:
    service = ticket_service or TicketService()

    try:
        ticket = service.create_ticket(customer_id=customer_id, reason=reason, priority=priority)
        result = ActionResult(ok=True, payload={"ticket": asdict(ticket)})
        return result.to_dict()
    except ValidationError as exc:
        return make_error(exc.code, exc.message).to_dict()
    except Exception:
        return make_error("INTERNAL_ERROR").to_dict()
