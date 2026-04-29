from app.models import CustomerRequest
from app.services import HandbookService
from app.workflows.main_workflow import SupportRequestWorkflow


class StubMcpClient:
    def __init__(self):
        self.lookup_calls = []
        self.refund_calls = []
        self.refund_history = []

    def get_customer_context(self, email: str):
        self.lookup_calls.append(email)
        return {
            "ok": True,
            "customer": {
                "customer_id": "cust_0001",
                "email": email,
                "name": "Alice",
                "plan_type": "Premium",
                "refund_history": list(self.refund_history),
            },
        }

    def record_refund_event(self, customer_id: str, amount: float, reason: str):
        self.refund_calls.append((customer_id, amount, reason))
        event = {
            "event_id": f"ref_{len(self.refund_calls):04d}",
            "customer_id": customer_id,
            "amount": amount,
            "reason": reason,
            "created_at": "2026-04-28T10:00:00Z",
        }
        self.refund_history.append(
            {
                "event_id": event["event_id"],
                "amount": amount,
                "reason": reason,
                "occurred_at": event["created_at"],
            }
        )
        return {"ok": True, "refund_event": event}


def _workflow(client: StubMcpClient):
    handbook = HandbookService("data/support_handbook.md")
    return SupportRequestWorkflow(handbook_service=handbook, mcp_client=client)


def test_refund_approval_records_event_and_mentions_reference() -> None:
    mcp = StubMcpClient()
    workflow = _workflow(mcp)

    request = CustomerRequest(
        raw_message=(
            "I was charged twice and want a refund for $49.99 on 04/10. "
            "my email is alice@example.com"
        ),
        request_id="req_refund_record",
    )

    state = workflow.execute(request, allow_clarification_prompt=False)

    assert len(mcp.refund_calls) == 1
    assert state.refund_event is not None
    assert state.response is not None
    assert "Reference:" in state.response.response_text


def test_recorded_refund_event_is_visible_on_later_context_lookup() -> None:
    mcp = StubMcpClient()
    workflow = _workflow(mcp)

    refund_request = CustomerRequest(
        raw_message=(
            "Please refund this billing error, I was charged twice for $29.99 on 04/11. "
            "alice@example.com"
        ),
        request_id="req_refund_first",
    )
    workflow.execute(refund_request, allow_clarification_prompt=False)

    follow_up = CustomerRequest(
        raw_message="Hi again, checking my account status at alice@example.com",
        request_id="req_refund_followup",
    )
    follow_state = workflow.execute(follow_up, allow_clarification_prompt=False)

    assert follow_state.customer_context is not None
    assert len(follow_state.customer_context["refund_history"]) == 1
    assert follow_state.customer_context["refund_history"][0]["event_id"].startswith("ref_")
