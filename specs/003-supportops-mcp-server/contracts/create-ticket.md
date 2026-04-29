# Contract: create_ticket Tool

**Tool Type**: Business action  
**Owner**: SupportOps MCP server

## Purpose

Create an escalation ticket as a concrete support action triggered by host policy decision.

## Input

```json
{
  "customer_id": "string",
  "reason": "string",
  "priority": "string"
}
```

## Validation

- `customer_id` is required and must exist.
- `reason` is required and non-empty.
- `priority` must be one of: `low`, `medium`, `high`, `urgent`.

## Success Response

```json
{
  "ok": true,
  "ticket": {
    "ticket_id": "tkt_20260426_0001",
    "customer_id": "cust_1001",
    "reason": "legal_threat",
    "priority": "high",
    "status": "open",
    "created_at": "2026-04-26T09:14:00Z"
  }
}
```

## Failure Response

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_PRIORITY",
    "message": "Priority must be one of low|medium|high|urgent"
  }
}
```

Possible error codes:
- `INVALID_ARGUMENT`
- `INVALID_PRIORITY`
- `CUSTOMER_NOT_FOUND`
- `INTERNAL_ERROR`
