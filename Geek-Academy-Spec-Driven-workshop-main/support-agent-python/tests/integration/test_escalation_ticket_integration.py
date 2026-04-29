from app.models import CustomerRequest
from app.services import HandbookService
from app.workflows.main_workflow import SupportRequestWorkflow


class StubMcpClient:
    def __init__(self, ticket_ok: bool = True):
        self.ticket_ok = ticket_ok
        self.lookup_calls = []
        self.ticket_calls = []

    def get_customer_context(self, email: str):
        self.lookup_calls.append(email)
        return {
            "ok": True,
            "customer": {
                "customer_id": "cust_0001",
                "email": email,
                "name": "Alice",
                "plan_type": "Premium",
                "refund_history": [],
            },
        }

    def create_ticket(self, customer_id: str, reason: str, priority: str):
        self.ticket_calls.append((customer_id, reason, priority))
        if self.ticket_ok:
            return {
                "ok": True,
                "ticket": {
                    "ticket_id": "tkt_0001",
                    "customer_id": customer_id,
                    "reason": reason,
                    "priority": priority,
                    "status": "open",
                    "created_at": "2026-04-28T10:00:00Z",
                },
            }
        return {
            "ok": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "ticket creation failed",
            },
        }


def _workflow(client: StubMcpClient):
    handbook = HandbookService("data/support_handbook.md")
    return SupportRequestWorkflow(handbook_service=handbook, mcp_client=client)


def test_escalation_invokes_create_ticket_and_includes_ticket_id() -> None:
    mcp = StubMcpClient(ticket_ok=True)
    workflow = _workflow(mcp)

    request = CustomerRequest(
        raw_message="This is unacceptable and I will contact my lawyer. My email is alice@example.com",
        request_id="req_escalation_action",
    )

    state = workflow.execute(request, allow_clarification_prompt=False)

    assert len(mcp.ticket_calls) == 1
    assert state.escalation_ticket is not None
    assert state.response is not None
    assert state.response.escalation_ticket_id == "tkt_0001"
    assert "tkt_0001" in state.response.response_text


def test_escalation_tool_failure_records_safe_fallback_error() -> None:
    mcp = StubMcpClient(ticket_ok=False)
    workflow = _workflow(mcp)

    request = CustomerRequest(
        raw_message="Manager now. This is fraud. email alice@example.com",
        request_id="req_escalation_action_fail",
    )

    state = workflow.execute(request, allow_clarification_prompt=False)

    assert len(mcp.ticket_calls) == 1
    assert state.escalation_ticket is None
    assert state.mcp_errors
    assert state.response is not None
    assert state.response.response_type == "escalation_notice"
