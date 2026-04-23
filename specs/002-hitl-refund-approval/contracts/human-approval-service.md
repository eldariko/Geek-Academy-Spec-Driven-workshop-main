# Contract: Human Approval Service

**Feature**: 002-hitl-refund-approval  
**Date**: 2026-04-17  
**Type**: Internal service interface

---

## Purpose

`HumanApprovalService` is the boundary between the automated workflow and the human operator. It is responsible for:

1. Receiving a `Recommendation` from the workflow
2. Presenting it to the operator via the console
3. Collecting the operator's decision
4. Recording an `AuditLogEntry`
5. Returning a `HumanDecision` to the workflow

---

## Interface

### `HumanApprovalService.__init__`

```python
def __init__(
    self,
    audit_log_path: Optional[str] = None,
    input_fn: Callable[[str], str] = input,
    operator_id: str = "console"
)
```

| Parameter        | Type                   | Default     | Description                                               |
| ---------------- | ---------------------- | ----------- | --------------------------------------------------------- |
| `audit_log_path` | `Optional[str]`        | `None`      | If set, audit entries are appended as JSONL to this path  |
| `input_fn`       | `Callable[[str], str]` | `input`     | Injectable input function; replace with a lambda in tests |
| `operator_id`    | `str`                  | `"console"` | Identity written to audit log entries                     |

---

### `HumanApprovalService.request_approval`

The primary method. Blocks until the operator provides a valid decision.

```python
def request_approval(self, recommendation: Recommendation) -> HumanDecision
```

**Inputs**:

- `recommendation`: A populated `Recommendation` dataclass (see data-model.md)

**Outputs**:

- `HumanDecision` with `decision`, `operator_note`, `operator_id`, `decided_at`, and `overrides_recommendation` filled

**Side effects**:

- Writes one `AuditLogEntry` to `self.audit_log`
- If `audit_log_path` is set, appends the entry as a JSONL line to that file

**Invariants**:

- The returned `HumanDecision.decision` is always `"approve"` or `"reject"` — never `None` or an unrecognized string
- `request_approval` never returns without a recorded `AuditLogEntry`
- The operator is shown the full recommendation before being asked for a decision

**Error behavior**:

- If the operator enters an unrecognized value, the prompt repeats until a valid value is entered (no limit on retries)
- If `audit_log_path` is set but the file cannot be written, an `IOError` is raised (the in-memory entry is already recorded)

---

### `HumanApprovalService.get_audit_log`

```python
def get_audit_log(self) -> list[AuditLogEntry]
```

Returns a shallow copy of the in-memory audit log. Entries are in insertion order.

---

## Console Prompt Schema

The service renders the following to stdout before collecting input:

```
=== HUMAN APPROVAL REQUIRED ===

Request ID  : {recommendation.request_id}
Agent Recommendation : {recommendation.suggested_decision.upper()}

Summary:
  {customer request text, truncated to 300 chars}

Agent Reasoning:
  {recommendation.reasoning}

Policies Applied:
  - {policy_1}
  - {policy_2}
  ...

Enter decision [approve/reject]: _
(Optional) Override note (press Enter to skip): _
```

---

## Testability Contract

For unit tests, `HumanApprovalService` must accept an injectable `input_fn`:

```python
# Simulate "approve" then empty note
service = HumanApprovalService(input_fn=iter(["approve", ""]).__next__)

decision = service.request_approval(recommendation)
assert decision.decision == "approve"
assert decision.overrides_recommendation == False
```

The injectable `input_fn` receives the prompt string and returns the operator's simulated response.
