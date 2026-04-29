# Quickstart: Human-in-the-Loop Refund Approval

**Feature**: 002-hitl-refund-approval  
**Date**: 2026-04-17

---

## What This Feature Adds

When a customer sends a **refund request**, the support agent now **pauses** before sending the customer-facing response. It shows the human operator:

- The customer's request
- The agent's recommendation (approve or reject) and why
- Which policies applied

The operator then types `approve` or `reject`, optionally adds a note, and the system resumes — generating and displaying the response based on the operator's decision.

All decisions are recorded in an audit log.

---

## How to Use

### Running Normally

No change to how you start the app:

```bash
cd support-agent-python
python main.py
```

When a refund request is submitted, you will see:

```
=== HUMAN APPROVAL REQUIRED ===

Request ID  : req_20260417_143022_ab12cd
Agent Recommendation : APPROVE

Summary:
  I'd like a refund, I signed up 2 weeks ago and haven't used it at all.

Agent Reasoning:
  Customer is within the 30-day refund window. No prior refund on record.
  First-time refund policy applies.

Policies Applied:
  - first_month_refund

Enter decision [approve/reject]: approve
(Optional) Override note (press Enter to skip):

=== ANSWER ===
We've processed your refund request...
```

### Audit Log File (optional)

Pass `--audit-log <path>` to persist all decisions to a JSONL file:

```bash
python main.py --audit-log ./audit.jsonl
```

Each line is a JSON object:

```json
{
	"entry_id": "abc123",
	"request_id": "req_20260417_143022_ab12cd",
	"agent_recommendation": "approve",
	"human_decision": "approve",
	"operator_note": "",
	"operator_id": "console",
	"is_override": false,
	"decided_at": "2026-04-17T14:30:45.123456"
}
```

---

## Non-Refund Requests

No change. Questions, cancellations, and escalations pass through without an approval step.

---

## Running Tests

```bash
cd support-agent-python
pytest tests/
```

Approval tests use injected input functions — no TTY or interactive input needed.

---

## Files Added/Modified

| File                               | Change                                                               |
| ---------------------------------- | -------------------------------------------------------------------- |
| `app/models/approval.py`           | New — `Recommendation`, `HumanDecision`, `AuditLogEntry` dataclasses |
| `app/models/__init__.py`           | Export new models                                                    |
| `app/services/approval_service.py` | New — `HumanApprovalService`                                         |
| `app/services/__init__.py`         | Export new service                                                   |
| `app/models/workflow_state.py`     | Add `human_decision` field                                           |
| `app/workflows/main_workflow.py`   | Add approval gate between Step 2 and Step 3                          |
| `app/agents/response_generator.py` | Read `state.human_decision` when present                             |
| `app/console_ui.py`                | Add `render_approval_prompt()` helper                                |
| `main.py`                          | Add optional `--audit-log` CLI argument                              |
| `tests/test_hitl_approval.py`      | New — unit tests for approval service and workflow gate              |
