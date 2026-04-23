# Implementation Plan: Human-in-the-Loop Refund Approval

**Branch**: `002-hitl-refund-approval` | **Date**: 2026-04-17 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/002-hitl-refund-approval/spec.md`

---

## Summary

Add a human approval gate to the existing Python support agent for all refund-classified requests. After the PolicyEngine evaluates a refund request, the workflow pauses and presents a structured `Recommendation` (approve/reject + reasoning) to the human operator via the console. The operator's decision (`HumanDecision`) is recorded in an `AuditLogEntry` and used by the ResponseAgent to generate the final customer-facing message. Non-refund requests are unaffected.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: stdlib only (`dataclasses`, `datetime`, `json`, `pathlib`, `uuid`, `typing`) — no new packages  
**Storage**: In-memory `list[AuditLogEntry]`; optional JSONL file appended via `--audit-log` CLI flag  
**Testing**: pytest (existing); injectable `input_fn` enables non-interactive unit tests  
**Target Platform**: Console / CLI  
**Project Type**: CLI agentic application  
**Performance Goals**: Operator decision recorded without latency overhead; non-refund paths add zero latency  
**Constraints**: No new external dependencies; backward compatible with all existing non-refund flows  
**Scale/Scope**: Single-session, single-operator; sequential request processing

---

## Constitution Check

The project constitution file contains only template placeholders — no active principles are defined. No gate violations to evaluate.

_Re-check after Phase 1 design_: Design uses the existing `WorkflowState` extension pattern (consistent with `classification`, `policy_evaluation`, `response` fields), no new abstractions beyond what the spec requires, no new dependencies. No violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/002-hitl-refund-approval/
├── plan.md                          # This file
├── research.md                      # Phase 0 output
├── data-model.md                    # Phase 1 output
├── quickstart.md                    # Phase 1 output
├── contracts/
│   ├── human-approval-service.md   # Phase 1 output
│   └── approval-gate-workflow.md   # Phase 1 output
└── tasks.md                         # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root — Python agent only)

```text
Geek-Academy-Spec-Driven-workshop-main/support-agent-python/
├── app/
│   ├── models/
│   │   ├── approval.py          ← NEW: Recommendation, HumanDecision, AuditLogEntry
│   │   ├── workflow_state.py    ← MODIFIED: add human_decision field
│   │   └── __init__.py          ← MODIFIED: export new models
│   ├── services/
│   │   ├── approval_service.py  ← NEW: HumanApprovalService
│   │   └── __init__.py          ← MODIFIED: export new service
│   ├── workflows/
│   │   └── main_workflow.py     ← MODIFIED: add approval gate (Step 2a)
│   ├── agents/
│   │   └── response_generator.py ← MODIFIED: read state.human_decision
│   └── console_ui.py            ← MODIFIED: add render_approval_prompt()
├── main.py                      ← MODIFIED: add --audit-log CLI argument
└── tests/
    └── test_hitl_approval.py    ← NEW: unit tests
```

**Structure Decision**: Extends the existing single-project layout. New code follows the established `app/models/`, `app/services/` pattern.

---

## Implementation Design

### New: `app/models/approval.py`

Three dataclasses:

```python
@dataclass
class Recommendation:
    request_id: str
    suggested_decision: Literal["approve", "reject"]
    reasoning: str
    policy_rules_applied: list[str]
    generated_at: datetime = field(default_factory=datetime.now)

@dataclass
class HumanDecision:
    request_id: str
    decision: Literal["approve", "reject"]
    operator_note: Optional[str]
    operator_id: str
    decided_at: datetime
    overrides_recommendation: bool

@dataclass
class AuditLogEntry:
    entry_id: str
    request_id: str
    agent_recommendation: Literal["approve", "reject"]
    agent_reasoning: str
    human_decision: Literal["approve", "reject"]
    operator_note: Optional[str]
    operator_id: str
    is_override: bool
    decided_at: datetime
```

---

### New: `app/services/approval_service.py`

`HumanApprovalService` — see [contracts/human-approval-service.md](contracts/human-approval-service.md) for full interface.

Key behaviors:

- `request_approval(recommendation)` → renders prompt → collects `approve`/`reject` (retries on invalid input) → collects optional note → constructs and returns `HumanDecision` → writes `AuditLogEntry`
- Audit entries written to in-memory list; optionally appended to JSONL file
- `input_fn` is injectable for tests (defaults to built-in `input`)

---

### Modified: `app/models/workflow_state.py`

Add one field:

```python
human_decision: Optional[HumanDecision] = None
```

No other changes. All existing code continues to work.

---

### Modified: `app/workflows/main_workflow.py`

`SupportRequestWorkflow.__init__` accepts optional `approval_service: Optional[HumanApprovalService] = None`.

In `execute()`, between Step 2 (PolicyEngine) and Step 3 (ResponseAgent):

```python
# Step 2a: Human Approval Gate (refund requests only)
if (
    classification.classified_intent == "refund_request"
    and not classification.escalation_reason
    and self.approval_service is not None
):
    recommendation = self._build_recommendation(state)
    human_decision = self.approval_service.request_approval(recommendation)
    state.human_decision = human_decision
    state.log_agent_step("HumanApproval", f"decision={human_decision.decision}", human_decision.overrides_recommendation)
```

`_build_recommendation(state)` constructs a `Recommendation` from `state.policy_evaluation` per the contract.

---

### Modified: `app/agents/response_generator.py`

In `generate(state)`, check for `state.human_decision` before determining response content:

```python
# Use human decision if present (overrides policy engine decision)
if state.human_decision is not None:
    effective_decision = state.human_decision.decision  # "approve" or "reject"
else:
    effective_decision = "approve" if state.policy_evaluation.is_approved else "reject"
```

The ResponseAgent then uses `effective_decision` to select the appropriate response template/prompt.

---

### Modified: `app/console_ui.py`

Add `render_approval_prompt(recommendation)` function that formats and prints the approval banner per the console prompt schema defined in the contract.

---

### Modified: `main.py`

Add `--audit-log <path>` optional argument. If provided, pass it to `HumanApprovalService(audit_log_path=...)`.  
Pass `HumanApprovalService` to `SupportRequestWorkflow` via `Orchestrator`.

`Orchestrator.__init__` gains an optional `approval_service` parameter forwarded to `SupportRequestWorkflow`.

---

### New: `tests/test_hitl_approval.py`

Test coverage:

1. `HumanApprovalService` — approve decision recorded correctly
2. `HumanApprovalService` — reject decision recorded correctly
3. `HumanApprovalService` — override flag set when decision differs from recommendation
4. `HumanApprovalService` — invalid input retries until valid
5. `HumanApprovalService` — audit log entry written with all fields
6. `HumanApprovalService` — JSONL file written when `audit_log_path` is set
7. Workflow gate — gate triggers for `refund_request` intent
8. Workflow gate — gate does NOT trigger for `simple_question`, `cancellation_request`, `escalation_needed`
9. Workflow gate — `state.human_decision` is `None` for non-refund requests
10. ResponseAgent — uses `state.human_decision.decision` when present (approve path)
11. ResponseAgent — uses `state.human_decision.decision` when present (reject path)

---

## Complexity Tracking

No constitution violations requiring justification.
