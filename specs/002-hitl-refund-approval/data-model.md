# Data Model: Human-in-the-Loop Refund Approval

**Feature**: 002-hitl-refund-approval  
**Date**: 2026-04-17

---

## New Entities

### `Recommendation`

The agent's structured output for a refund-flagged request. Produced by the workflow after PolicyEngine completes, before any response is sent to the customer.

| Field                  | Type                           | Description                                               |
| ---------------------- | ------------------------------ | --------------------------------------------------------- |
| `request_id`           | `str`                          | Links to the originating `CustomerRequest`                |
| `suggested_decision`   | `Literal["approve", "reject"]` | Agent's recommended outcome                               |
| `reasoning`            | `str`                          | Plain-language justification drawn from policy evaluation |
| `policy_rules_applied` | `list[str]`                    | Names of the policy rules that led to this recommendation |
| `generated_at`         | `datetime`                     | When the recommendation was created                       |

**Validation rules**:

- `suggested_decision` must be exactly `"approve"` or `"reject"`
- `reasoning` must be non-empty
- `request_id` must match an active `CustomerRequest`

**State transitions**: Created once per refund request → consumed by `HumanApprovalService` → immutable after creation

---

### `HumanDecision`

The operator's recorded response to a `Recommendation`. Captured interactively via the console.

| Field                      | Type                           | Description                                                         |
| -------------------------- | ------------------------------ | ------------------------------------------------------------------- |
| `request_id`               | `str`                          | Links to the originating `CustomerRequest`                          |
| `decision`                 | `Literal["approve", "reject"]` | The operator's chosen outcome                                       |
| `operator_note`            | `Optional[str]`                | Free-text override note; empty string or `None` = no note provided  |
| `operator_id`              | `str`                          | Operator identity; defaults to `"console"` for single-user sessions |
| `decided_at`               | `datetime`                     | Timestamp when the decision was recorded                            |
| `overrides_recommendation` | `bool`                         | `True` if `decision` differs from the agent's `suggested_decision`  |

**Validation rules**:

- `decision` must be exactly `"approve"` or `"reject"`
- `operator_note` may be empty; no minimum length enforced
- `decided_at` is set at the moment the operator confirms their choice (not when the prompt is shown)

---

### `AuditLogEntry`

Immutable record linking a `Recommendation` to a `HumanDecision`. Written immediately after the decision is recorded.

| Field                  | Type                           | Description                                          |
| ---------------------- | ------------------------------ | ---------------------------------------------------- |
| `entry_id`             | `str`                          | UUID; unique identifier for this audit record        |
| `request_id`           | `str`                          | Links to the originating `CustomerRequest`           |
| `agent_recommendation` | `Literal["approve", "reject"]` | The agent's suggested outcome                        |
| `agent_reasoning`      | `str`                          | Copied from `Recommendation.reasoning`               |
| `human_decision`       | `Literal["approve", "reject"]` | The operator's chosen outcome                        |
| `operator_note`        | `Optional[str]`                | Copied from `HumanDecision.operator_note`            |
| `operator_id`          | `str`                          | Copied from `HumanDecision.operator_id`              |
| `is_override`          | `bool`                         | `True` when `human_decision != agent_recommendation` |
| `decided_at`           | `datetime`                     | Copied from `HumanDecision.decided_at`               |

**Validation rules**:

- Once written, an `AuditLogEntry` is never modified
- All fields are required (no optional fields except `operator_note`)
- `entry_id` is generated as `uuid.uuid4().hex` at write time

**Persistence**: Stored in `HumanApprovalService.audit_log: list[AuditLogEntry]`. If `audit_log_path` is set, also appended to a JSONL file as a single JSON line.

---

## Modified Entities

### `WorkflowState` (existing — extended)

One new optional field added:

| Field            | Type                      | Description                                                              |
| ---------------- | ------------------------- | ------------------------------------------------------------------------ |
| `human_decision` | `Optional[HumanDecision]` | Set when a human approval step completes; `None` for non-refund requests |

No existing fields are modified. Backward compatibility is preserved — all code that reads `WorkflowState` without checking `human_decision` continues to work unchanged.

---

## Entity Relationships

```
CustomerRequest (existing)
    │
    ├──► ClassificationResult (existing)   [classified_intent == "refund_request"]
    │
    ├──► PolicyEvaluation (existing)       [produces final_decision + reasoning]
    │
    ├──► Recommendation (NEW)              [derived from PolicyEvaluation; displayed to operator]
    │
    ├──► HumanDecision (NEW)               [operator input; overrides or confirms Recommendation]
    │
    ├──► AuditLogEntry (NEW)               [immutable record; Recommendation + HumanDecision]
    │
    └──► SupportResponse (existing)        [generated using HumanDecision.decision]
```

---

## Enumerations

### `ApprovalDecision`

```python
"approve"  # Refund will be processed / confirmed to customer
"reject"   # Refund will not be processed; customer receives decline message
```

Used by both `Recommendation.suggested_decision`, `HumanDecision.decision`, and `AuditLogEntry` fields.
