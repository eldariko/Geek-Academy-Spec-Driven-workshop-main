"""Entry point for the SupportOps MCP server (Lab 2)."""

from app.config import SERVER_HOST, SERVER_NAME, SERVER_PATH, SERVER_PORT
from app.services.customer_store import CustomerStore
from app.services.refund_service import RefundService
from app.services.ticket_service import TicketService
from app.tools.create_ticket import create_ticket
from app.tools.get_customer_context import get_customer_context
from app.tools.record_refund_event import record_refund_event


def build_server():
    """Create and configure the MCP server with registered tools."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        SERVER_NAME,
        host=SERVER_HOST,
        port=SERVER_PORT,
        streamable_http_path=SERVER_PATH,
    )
    customer_store = CustomerStore()
    ticket_service = TicketService(store=customer_store)
    refund_service = RefundService(store=customer_store)

    @mcp.tool(name="get_customer_context")
    def get_customer_context_tool(email: str) -> dict:
        return get_customer_context(email, store=customer_store)

    @mcp.tool(name="create_ticket")
    def create_ticket_tool(customer_id: str, reason: str, priority: str) -> dict:
        return create_ticket(customer_id=customer_id, reason=reason, priority=priority, ticket_service=ticket_service)

    @mcp.tool(name="record_refund_event")
    def record_refund_event_tool(customer_id: str, amount: float, reason: str) -> dict:
        return record_refund_event(customer_id=customer_id, amount=amount, reason=reason, refund_service=refund_service)

    return mcp


def main() -> None:
    server = build_server()
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
