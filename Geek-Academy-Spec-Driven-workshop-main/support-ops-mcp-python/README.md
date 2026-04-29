# SupportOps MCP Server (Python)

Standalone MCP server project for Lab 2.

## Purpose

This project is separate from the Lab 1 host app and is intended to expose:

- At least one data-access tool (for example: customer lookup)
- At least one support action tool (for example: create ticket)

## Implemented Tools

- `get_customer_context(email: string)`
- `create_ticket(customer_id: string, reason: string, priority: string)`
- `record_refund_event(customer_id: string, amount: float, reason: string)`

Tool contracts are implemented with explicit success/failure envelopes:

- Success: `{"ok": true, ...}`
- Failure: `{"ok": false, "error": {"code": "...", "message": "..."}}`

## Local Run

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python main.py
```

Default endpoint:

- `http://localhost:5058/mcp`

## Validation Rules

- Email must be required, non-empty, and normalized to lowercase.
- `plan_type` must be one of `Basic|Premium`.
- Ticket priority must be one of `low|medium|high|urgent`.
- Refund amount must be strictly greater than zero.

## Inspector Check

Use MCP Inspector with Streamable HTTP and connect to `http://localhost:5058/mcp`.
Verify all three tools appear and that at least one data call and one action call succeed.

## Next Steps

1. Create and activate a virtual environment.
2. Install MCP server dependencies.
3. Implement tools over mock customer data.
4. Run the server locally (recommended: Streamable HTTP transport).
5. Validate with MCP Inspector.
6. Integrate your Lab 1 host app to call this server.
