# Contract: get_customer_context Tool

**Tool Type**: Data access  
**Owner**: SupportOps MCP server

## Purpose

Return customer profile context used by the host for personalization and policy evaluation.

## Input

```json
{
  "email": "string"
}
```

## Validation

- `email` is required.
- `email` must be non-empty and normalized to lowercase.

## Success Response

```json
{
  "ok": true,
  "customer": {
    "customer_id": "cust_1001",
    "email": "alex@example.com",
    "name": "Alex Chen",
    "plan_type": "Premium",
    "refund_history": [
      {
        "event_id": "ref_001",
        "amount": 19.99,
        "reason": "accidental_charge",
        "occurred_at": "2026-03-14T10:20:00Z"
      }
    ]
  }
}
```

## Failure Response

```json
{
  "ok": false,
  "error": {
    "code": "CUSTOMER_NOT_FOUND",
    "message": "No customer found for the supplied email"
  }
}
```

Possible error codes:
- `INVALID_ARGUMENT`
- `CUSTOMER_NOT_FOUND`
- `INTERNAL_ERROR`
