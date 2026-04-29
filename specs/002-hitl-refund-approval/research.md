# Research: Human-in-the-Loop Refund Approval

**Feature**: 002-hitl-refund-approval  
**Date**: 2026-04-17  
**Status**: Complete — all NEEDS CLARIFICATION items resolved

---

## 1. Where does the approval gate fit in the existing workflow?

**Decision**: Insert gate between Step 2 (PolicyEngine) and Step 3 (ResponseAgent) inside `SupportRequestWorkflow.execute()`.

**Rationale**: The PolicyEngine outputs `final_decision` (APPROVE / DENY / etc.) which is exactly the input to the recommendation. The ResponseAgent must be called _after_ the human decision is recorded, so it can generate the correct customer-facing message. Inserting here is the minimal, non-breaking change.

**Alternatives considered**:

- After ResponseAgent (post-generation review): Rejected — the response is already generated, making human override purely cosmetic
- In Orchestrator before workflow execution: Rejected — PolicyEngine hasn't run yet; no recommendation to show
- As a separate workflow step class: Considered; deferred to future if workflow grows significantly

---

## 2. How is a refund request detected?

**Decision**: Check `classification.classified_intent == "refund_request"` (existing `ClassifierAgent` output).

**Rationale**: The `ClassifierAgent` already distinguishes `"refund_request"` from `"simple_question"`, `"cancellation_request"`, and `"escalation_needed"`. No new classification logic is needed.

**Alternatives considered**:

- New confidence-threshold flag: Rejected — the existing intent is sufficient; adding a confidence check can be a future refinement
- Keyword-based secondary check: Rejected — redundant with the classifier

---

## 3. How is the human's decision communicated to the ResponseAgent?

**Decision**: Add an optional `human_decision: Optional[HumanDecision]` field to `WorkflowState`. The ResponseAgent checks this field and adjusts tone/content accordingly.

**Rationale**: `WorkflowState` is already the canonical state object passed through all agents. Adding a field is consistent with the existing pattern (classification, policy_evaluation, response all live there). The ResponseAgent already reads `state.policy_evaluation.final_decision`; it will additionally read `state.human_decision.decision` when present.

**Alternatives considered**:

- Separate `ApprovalContext` wrapper around WorkflowState: Rejected — adds indirection for a single field
- Passing decision directly into ResponseAgent.generate(): Rejected — breaks existing signature and creates an inconsistency

---

## 4. Console interaction pattern

**Decision**: Follow the existing `_collect_clarification_once()` pattern: check `sys.stdin.isatty()`, use `input()` for interactive prompt, allow injection of a callable for testability.

**Rationale**: The project already uses this pattern for clarification prompts. Consistency is preferable over introducing a new interaction library.

**Implementation**: `HumanApprovalService` accepts an optional `input_fn: Callable[[str], str]` (defaults to built-in `input`). Tests inject a lambda to simulate operator input without needing a TTY.

---

## 5. Audit log storage

**Decision**: In-memory `list[AuditLogEntry]` stored on `HumanApprovalService`. If an optional `audit_log_path: str` is provided at construction, each entry is additionally appended as a JSONL line to that file.

**Rationale**: Matches spec assumption ("in-memory or local file store"). No new dependencies required (stdlib `json`, `pathlib`). JSONL format is append-only, human-readable, and trivially parseable.

**Alternatives considered**:

- SQLite: Rejected — adds external storage concern; over-engineered for current scope
- Structured logging only: Rejected — spec requires a queryable audit log, not just log lines

---

## 6. New dependencies

**Decision**: None. All new code uses Python stdlib only (`dataclasses`, `datetime`, `json`, `pathlib`, `typing`).

**Rationale**: Spec constraint: "no new external dependencies". Existing dependencies (pytest, ruff) are sufficient.

---

## Summary Table

| Unknown                    | Decision                                 | Files Affected                                                     |
| -------------------------- | ---------------------------------------- | ------------------------------------------------------------------ |
| Gate location              | After PolicyEngine, before ResponseAgent | `app/workflows/main_workflow.py`                                   |
| Refund detection           | `classified_intent == "refund_request"`  | No change to classifier                                            |
| Human decision propagation | `WorkflowState.human_decision` field     | `app/models/workflow_state.py`, `app/agents/response_generator.py` |
| Console interaction        | `input()` with injectable `input_fn`     | `app/console_ui.py`, new `app/services/approval_service.py`        |
| Audit log                  | In-memory list + optional JSONL file     | new `app/services/approval_service.py`                             |
| New dependencies           | None                                     | `requirements.txt` unchanged                                       |
