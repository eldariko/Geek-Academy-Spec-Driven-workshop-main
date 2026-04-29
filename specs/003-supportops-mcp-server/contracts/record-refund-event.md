# Contract: record_refund_event Tool

**Tool Type**: Business action  
**Owner**: SupportOps MCP server

## Purpose

Record a successful refund event so future customer context reflects updated refund history.

## Input

```json
{
  "customer_id": "string",
  "amount": 29.99,
  "reason": "string"
}
```

## Validation

- `customer_id` is required and must exist.
- `amount` is required and must be `> 0`.
- `reason` is required and non-empty.

## Success Response

```json
{
  "ok": true,
  "refund_event": {
    "event_id": "ref_20260426_0003",
    "customer_id": "cust_1001",
    "amount": 29.99,
    "reason": "service_not_as_expected",
    "created_at": "2026-04-26T09:20:00Z"
  }
}
```

## Failure Response

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_AMOUNT",
    "message": "Refund amount must be greater than zero"
  }
}
```

Possible error codes:
- `INVALID_ARGUMENT`
- `INVALID_AMOUNT`
- `CUSTOMER_NOT_FOUND`
- `INTERNAL_ERROR`
