# Data Model: SupportOps MCP Server

**Feature**: 003-supportops-mcp-server  
**Date**: 2026-04-26

## Entities

### CustomerContext

Ground-truth customer profile returned by MCP for host personalization and policy evaluation inputs.

| Field | Type | Description |
|---|---|---|
| customer_id | string | Stable customer identifier used for follow-up actions |
| email | string | Lookup key used by host |
| name | string | Customer display name for personalization |
| plan_type | enum(`Basic`,`Premium`) | Current subscription plan |
| refund_history | list[RefundHistoryItem] | Prior refund events for policy checks |

**Validation rules**:
- `email` must be normalized to lowercase before lookup.
- `plan_type` must be one of `Basic` or `Premium`.
- `refund_history` may be empty but must always be present.

### RefundHistoryItem

Historical refund record attached to a customer profile.

| Field | Type | Description |
|---|---|---|
| event_id | string | Unique refund event identifier |
| amount | float | Refunded amount |
| reason | string | Refund reason |
| occurred_at | string (ISO 8601) | Timestamp of refund event |

**Validation rules**:
- `amount` must be greater than `0`.
- `occurred_at` must be valid ISO timestamp.

### SupportTicket

Escalation action record created by MCP.

| Field | Type | Description |
|---|---|---|
| ticket_id | string | Unique ticket identifier returned to host |
| customer_id | string | Customer the escalation is for |
| reason | string | Escalation reason text |
| priority | enum(`low`,`medium`,`high`,`urgent`) | Escalation priority |
| status | enum(`open`) | Initial status for workshop scope |
| created_at | string (ISO 8601) | Ticket creation timestamp |

**Validation rules**:
- `customer_id` must reference an existing customer.
- `reason` must be non-empty.
- `priority` must match allowed values.

### RefundEvent

Business action record created when a refund is approved and executed.

| Field | Type | Description |
|---|---|---|
| event_id | string | Unique refund event identifier |
| customer_id | string | Customer receiving the refund |
| amount | float | Approved refund amount |
| reason | string | Refund reason |
| created_at | string (ISO 8601) | Event creation timestamp |

**Validation rules**:
- `amount` must be strictly positive.
- `reason` must be non-empty.
- `customer_id` must reference an existing customer.

### PolicyDecision (Host-owned)

Host orchestration output that determines whether an MCP action is required.

| Field | Type | Description |
|---|---|---|
| request_id | string | Current support request id |
| outcome | enum(`respond`,`escalate`,`refund`) | Decision after handbook policy evaluation |
| rationale | string | Policy explanation for traceability |
| action_payload | object? | Optional action input for MCP tool calls |

**Validation rules**:
- `outcome` determines whether `action_payload` is required.
- `rationale` must be non-empty.

## Relationships

- One `CustomerContext` can have many `RefundHistoryItem` records.
- One `CustomerContext` can have many `SupportTicket` records over time.
- One `CustomerContext` can have many `RefundEvent` records over time.
- A `PolicyDecision` may trigger either one `SupportTicket` creation or one `RefundEvent` creation for a single request.

## State Transitions

### Escalation path

1. Host creates `PolicyDecision(outcome=escalate)`.
2. Host calls `create_ticket(...)`.
3. MCP creates `SupportTicket(status=open)` and returns action result.
4. Host emits final escalation response including ticket reference.

### Refund path

1. Host creates `PolicyDecision(outcome=refund)`.
2. Host calls `record_refund_event(...)`.
3. MCP creates `RefundEvent` and appends it to customer refund history.
4. Future `get_customer_context(...)` calls include this event.
