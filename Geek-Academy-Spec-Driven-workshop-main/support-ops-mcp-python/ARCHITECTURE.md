# SupportOps MCP Server Architecture

## Overview

`support-ops-mcp-python` is a standalone MCP server that exposes support operations over Streamable HTTP. It is designed to be called by a host application, such as `support-agent-python`, rather than by end users directly.

Current responsibilities:

- expose customer context lookup
- expose operational support actions
- validate tool inputs at the tool/service boundary
- return explicit success/failure envelopes
- keep operational state in memory for the lifetime of the process

Entry point: `main.py`.

## High-Level Architecture

The server follows a simple layered design:

1. MCP host layer: FastMCP server setup and tool registration.
2. Tool handler layer: thin MCP-facing functions with error envelope mapping.
3. Service layer: validation and business action logic.
4. Store layer: mock customer data loading and in-memory state mutation.
5. Model layer: domain and response-envelope dataclasses.

This keeps transport concerns separate from business rules and makes the tool contracts easy to test directly.

## Request Flow

For each MCP tool call:

1. A client calls the server at `http://127.0.0.1:5058/mcp`.
2. FastMCP routes the request to the registered Python tool function.
3. The tool handler validates or delegates validation.
4. The service executes the action using `CustomerStore` or in-memory action state.
5. The handler returns a JSON-compatible envelope:
   - success: `{"ok": true, ...}`
   - failure: `{"ok": false, "error": {"code": "...", "message": "..."}}`

## Runtime Composition

`main.py` builds the server in one place:

- creates `FastMCP`
- instantiates a shared `CustomerStore`
- instantiates `TicketService` and `RefundService` with that shared store
- registers three MCP tools against those instances
- runs the server with `transport="streamable-http"`

This shared composition is important because it allows ticket/refund actions to work against the same loaded customer dataset for the life of the process.

## Tool Surface

Implemented tools:

- `get_customer_context(email)`
- `create_ticket(customer_id, reason, priority)`
- `record_refund_event(customer_id, amount, reason)`

### `get_customer_context`

- Normalizes email to lowercase.
- Looks up a customer in the mock data store.
- Returns a serialized `CustomerContext` if found.

### `create_ticket`

- Validates `customer_id`, `reason`, and `priority`.
- Confirms the customer exists.
- Creates an in-memory `SupportTicket` with deterministic IDs like `tkt_0001`.

### `record_refund_event`

- Validates `customer_id`, `amount`, and `reason`.
- Confirms the customer exists.
- Appends a refund event to the customer’s in-memory refund history.
- Returns a `RefundEvent` with deterministic IDs like `ref_0001`.

## Module Responsibilities

### Host and Config

- `main.py`
  - server construction and tool registration
  - dependency wiring
  - transport startup

- `app/config.py`
  - server identity and bind settings
  - default mock customer data path

### Tool Handlers

- `app/tools/get_customer_context.py`
- `app/tools/create_ticket.py`
- `app/tools/record_refund_event.py`

These are intentionally thin adapters. They translate service results and exceptions into stable MCP response envelopes.

### Services

- `app/services/customer_store.py`
  - loads `mock-data-lab2/mock_customers.json`
  - builds customer indexes by email and customer ID
  - stores refund history in memory

- `app/services/ticket_service.py`
  - creates validated support tickets
  - stores tickets in an in-memory list

- `app/services/refund_service.py`
  - validates and records refund events
  - delegates persistence to `CustomerStore`

- `app/services/validators.py`
  - contract-first validation helpers
  - email normalization and field validation

- `app/services/error_mapper.py`
  - maps known errors into a standard tool error payload

### Models

- `app/models/domain.py`
  - `CustomerContext`
  - `RefundHistoryItem`
  - `SupportTicket`
  - `RefundEvent`

- `app/models/results.py`
  - `ToolError`
  - `ToolSuccess`
  - `ActionResult`

## Data and State Model

### Source Data

Customer records are loaded from:

- `mock-data-lab2/mock_customers.json`

The store converts that dataset into runtime `CustomerContext` objects and assigns deterministic customer IDs (`cust_0001`, `cust_0002`, ...).

### In-Memory State

The server is intentionally stateful only within a single process:

- ticket state is kept in `TicketService._tickets`
- refund history is attached to `CustomerContext.refund_history`

This means action state is not durable across server restarts.

## Validation Boundary

Validation is explicit and centralized.

Important rules enforced today:

- `email` is required, non-empty, and normalized to lowercase
- `plan_type` must be `Basic` or `Premium`
- `priority` must be `low`, `medium`, `high`, or `urgent`
- `amount` must be numeric and greater than zero

Validation failures raise `ValidationError`, which tool handlers convert into stable error envelopes.

## Error Handling Strategy

The server uses a consistent contract-first error model:

- validation failures return domain-specific error codes like `INVALID_ARGUMENT`, `INVALID_PRIORITY`, or `INVALID_AMOUNT`
- missing customers return `CUSTOMER_NOT_FOUND`
- unexpected exceptions are collapsed to `INTERNAL_ERROR`

This is important for host clients, because they can branch on machine-readable error codes without parsing free text.

## Transport and Integration Model

- transport: Streamable HTTP
- host: `127.0.0.1`
- port: `5058`
- path: `/mcp`

The server is intended to be called by an MCP-aware host orchestrator. In this repository, `support-agent-python` uses a matching `SupportOpsMcpClient` to call these tools.

## Design Characteristics

Current design properties:

- synchronous process model with simple local state
- explicit contracts instead of implicit exceptions
- no external database or queue
- deterministic IDs for local development and testing
- minimal transport surface: three tools only

## Current Constraints

- ticket and refund actions are not persisted across restarts
- customer data is loaded from a static mock JSON file
- no authentication or authorization layer is implemented
- no concurrency controls are present for multi-process or multi-instance deployment
- store and action state are suitable for labs and local development, not production deployment

## Suggested Future Evolution

- add durable persistence for tickets and refund events
- separate repository/storage interfaces from service logic
- add request logging and structured tool metrics
- define versioned tool contracts if the host app will evolve independently
- add authentication if the server is exposed beyond localhost
