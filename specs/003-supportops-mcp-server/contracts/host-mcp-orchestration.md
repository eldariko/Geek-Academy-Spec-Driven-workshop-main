# Contract: Host <-> MCP Orchestration

**Pattern**: Host-orchestrated workflow with MCP tool invocations

## Canonical Flow

```text
Customer Request
  -> Host Classifier
  -> MCP.get_customer_context(email)
  -> Host Policy Evaluation (support_handbook.md)
  -> if escalate: MCP.create_ticket(...)
  -> if refund-approved: MCP.record_refund_event(...)
  -> Host Final Response
```

## Rules

1. Host is the sole decision-maker for policy outcomes.
2. MCP does not evaluate handbook policy; MCP only returns data and executes actions.
3. Host must call `get_customer_context` before policy decision for known-email requests.
4. Escalation decisions must call `create_ticket`; text-only escalation is not valid.
5. Approved refund decisions must call `record_refund_event` before final response.
6. Any MCP tool failure must produce a safe fallback response and a traceable log entry.

## Host Input to MCP

- `email` from customer request identity context.
- `customer_id` from `get_customer_context` response.
- `reason` and `priority` from host classification + policy result.
- `amount` for refund from policy output.

## Host Output Guarantees

- Response includes personalization when customer context is available.
- Escalation responses include ticket reference when creation succeeds.
- Refund responses are only marked complete after refund event record succeeds.
