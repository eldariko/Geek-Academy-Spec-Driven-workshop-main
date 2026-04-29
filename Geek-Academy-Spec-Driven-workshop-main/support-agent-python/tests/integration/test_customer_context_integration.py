from app.models import CustomerRequest
from app.services import HandbookService
from app.workflows.main_workflow import SupportRequestWorkflow


class StubMcpClient:
    def __init__(self, payload=None):
        self.payload = payload
        self.calls = []

    def get_customer_context(self, email: str):
        self.calls.append(email)
        if self.payload is None:
            return {
                "ok": False,
                "error": {
                    "code": "CUSTOMER_NOT_FOUND",
                    "message": "No customer found for the supplied email",
                },
            }
        return {"ok": True, "customer": self.payload}


def _workflow_with_client(client):
    handbook = HandbookService("data/support_handbook.md")
    return SupportRequestWorkflow(handbook_service=handbook, mcp_client=client)


def test_customer_context_personalizes_response_for_known_customer() -> None:
    customer = {
        "customer_id": "cust_0001",
        "email": "alice@example.com",
        "name": "Alice",
        "plan_type": "Premium",
        "refund_history": [],
    }
    mcp_client = StubMcpClient(payload=customer)
    workflow = _workflow_with_client(mcp_client)

    request = CustomerRequest(
        raw_message="Hi, I have a billing question. My email is alice@example.com",
        request_id="req_customer_context_known",
    )

    state = workflow.execute(request, allow_clarification_prompt=False)

    assert mcp_client.calls == ["alice@example.com"]
    assert state.customer_context is not None
    assert state.customer_context["plan_type"] == "Premium"
    assert state.response is not None
    text = state.response.response_text
    assert "Alice" in text
    assert "Premium" in text


def test_customer_context_unknown_customer_uses_safe_fallback() -> None:
    mcp_client = StubMcpClient(payload=None)
    workflow = _workflow_with_client(mcp_client)

    request = CustomerRequest(
        raw_message="Can you help? my email is missing@example.com",
        request_id="req_customer_context_missing",
    )

    state = workflow.execute(request, allow_clarification_prompt=False)

    assert mcp_client.calls == ["missing@example.com"]
    assert state.customer_context is None
    assert state.response is not None
    text = state.response.response_text.lower()
    assert "thanks" in text or "thank you" in text
