# Tasks: Human-in-the-Loop Refund Approval

**Input**: Design documents from `/specs/002-hitl-refund-approval/`  
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: Included — acceptance scenarios from spec.md require test coverage

**Organization**: Tasks grouped by user story. Each story is independently testable and implementable.

---

## Format Reference

- **[ID]**: Sequential task identifier (T001, T002, ...)
- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: User story label (US1, US2, US3, US4)
- Paths: `support-agent-python/app/...` prefix omitted; assume root is `support-agent-python/`

---

## Phase 1: Setup

**Purpose**: Project initialization

- [X] T001 No setup tasks required — extending existing support-agent-python project

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the HITL infrastructure that all user stories depend on

**⚠️ CRITICAL**: All tasks in this phase must complete before user story work begins

### Data Models & Service

- [X] T002 Create `app/models/approval.py` with three dataclasses: `Recommendation`, `HumanDecision`, `AuditLogEntry`
- [X] T003 [P] Update `app/models/__init__.py` to export `Recommendation`, `HumanDecision`, `AuditLogEntry`
- [X] T004 Create `app/services/approval_service.py` with `HumanApprovalService` class (see contracts/human-approval-service.md)
- [X] T005 [P] Update `app/services/__init__.py` to export `HumanApprovalService`
- [X] T006 Extend `app/models/workflow_state.py` with optional `human_decision: Optional[HumanDecision] = None` field

### Workflow Integration

- [X] T007 Modify `app/workflows/main_workflow.py`: add approval gate (Step 2a) between PolicyEngine and ResponseAgent per contracts/approval-gate-workflow.md
- [X] T008 [P] Modify `app/agents/response_generator.py`: read `state.human_decision` when present; use it to determine response outcome
- [X] T009 [P] Add `render_approval_prompt(recommendation: Recommendation)` helper to `app/console_ui.py` per console prompt schema in contracts/

### CLI & Entry Point

- [X] T010 Modify `main.py`: add optional `--audit-log <path>` CLI argument; pass audit_log_path to `Orchestrator`
- [X] T011 Modify `app/orchestrator.py`: accept optional `approval_service: HumanApprovalService` parameter; pass to `SupportRequestWorkflow`

**Checkpoint**: HITL infrastructure complete. Approval gate is wired into workflow. Non-refund requests pass through unchanged.

---

## Phase 3: User Story 1 - Human Approves Refund Recommendation (Priority: P1) 🎯

**Goal**: Operator approves agent's approve recommendation; customer receives refund confirmation

**Independent Test**: Submit refund request within 30-day window → agent recommends approve → operator enters "approve" → audit log records decision → customer sees confirmation message

### Tests for User Story 1

- [X] T012 [US1] Create `tests/test_hitl_approval.py` with test class `TestApprovalService`
- [X] T013 [P] [US1] Unit test: `test_request_approval_approve_recorded_correctly()` — verify HumanApprovalService records approve decision with operator_id and timestamp
- [X] T014 [P] [US1] Unit test: `test_audit_entry_created_on_approve()` — verify AuditLogEntry written with all fields (entry_id, agent_recommendation, human_decision, operator_id, decided_at)
- [X] T015 [P] [US1] Unit test: `test_override_flag_false_when_no_override()` — verify `overrides_recommendation=False` when operator approves agent's approve recommendation
- [X] T016 [US1] Integration test: `test_workflow_approve_recommendation_generates_refund_response()` — end-to-end: classify as refund → policy approve → show prompt → operator approve → verify response confirms refund

### Implementation for User Story 1

- [X] T017 [US1] Verify ResponseAgent generates refund confirmation message when `human_decision.decision == "approve"` (triggered by T016 test)
- [X] T018 [US1] Add approval decision logging to `WorkflowState.agent_log` after human decision recorded

**Checkpoint**: User Story 1 complete. Approval workflow works for accept path. Tests passing.

---

## Phase 4: User Story 2 - Human Rejects Refund Recommendation (Priority: P1)

**Goal**: Operator rejects agent's approve recommendation; customer receives decline message without seeing recommendation

**Independent Test**: Submit refund request → agent recommends approve → operator enters "reject" → audit log records override decision → customer sees decline message (no mention of agent's recommendation)

### Tests for User Story 2

- [X] T019 [P] [US2] Unit test: `test_request_approval_reject_recorded_correctly()` — verify HumanApprovalService records reject decision
- [X] T020 [P] [US2] Unit test: `test_override_flag_true_when_reject_overrides_approve()` — verify `overrides_recommendation=True` when operator rejects agent's approve recommendation
- [X] T021 [P] [US2] Unit test: `test_audit_entry_is_override_flag()` — verify `AuditLogEntry.is_override=True` when decision ≠ recommendation
- [X] T022 [US2] Unit test: `test_operator_note_captured_in_audit()` — verify optional operator note is recorded in AuditLogEntry
- [X] T023 [US2] Integration test: `test_workflow_reject_recommendation_generates_decline_response()` — end-to-end: classify as refund → policy approve → operator reject → verify response declines refund, does NOT mention agent recommendation

### Implementation for User Story 2

- [X] T024 [US2] Verify ResponseAgent generates decline message when `human_decision.decision == "reject"` (triggered by T023 test)

**Checkpoint**: User Story 2 complete. Operator can override approve→reject. Tests passing.

---

## Phase 5: User Story 3 - Agent Recommends Rejection, Human Approves Instead (Priority: P2)

**Goal**: Operator approves as goodwill gesture; override agent's reject recommendation; customer receives approval (as exception)

**Independent Test**: Submit refund request outside policy window → agent recommends reject → operator enters "approve" and optional note (e.g., "goodwill") → audit log records override + note → customer sees refund confirmation

### Tests for User Story 3

- [X] T025 [P] [US3] Unit test: `test_override_flag_true_when_approve_overrides_reject()` — verify `overrides_recommendation=True` when operator approves agent's reject recommendation
- [X] T026 [P] [US3] Unit test: `test_audit_entry_notes_override_direction()` — verify audit log correctly records reject→approve override with agent_recommendation="reject", human_decision="approve"
- [X] T027 [US3] Integration test: `test_workflow_approve_overrides_reject_recommendation()` — end-to-end: classify as refund → policy deny → operator approve with note → verify response approves refund, audit captures note

### Implementation for User Story 3

- (No new implementation — infrastructure from Phase 2 already supports this path. Tests verify it works.)

**Checkpoint**: User Story 3 complete. Bidirectional override works. Tests passing.

---

## Phase 6: User Story 4 - Non-Refund Requests Pass Through Without Interruption (Priority: P1)

**Goal**: General questions, cancellations, escalations skip approval gate entirely; operator efficiency unaffected

**Independent Test**: Submit general question → no approval prompt shown → response delivered directly. Repeat for cancellation and escalation requests.

### Tests for User Story 4

- [X] T028 [P] [US4] Unit test: `test_gate_does_not_trigger_simple_question()` — verify approval gate NOT activated for `classified_intent="simple_question"`
- [X] T029 [P] [US4] Unit test: `test_gate_does_not_trigger_cancellation()` — verify approval gate NOT activated for `classified_intent="cancellation_request"`
- [X] T030 [P] [US4] Unit test: `test_gate_does_not_trigger_escalation()` — verify approval gate NOT activated for `classified_intent="escalation_needed"`
- [X] T031 [P] [US4] Unit test: `test_state_human_decision_none_for_non_refund()` — verify `state.human_decision` remains `None` for non-refund intents
- [X] T032 [US4] Integration test: `test_simple_question_workflow_unchanged()` — end-to-end general question → no approval step → response delivered directly
- [X] T033 [US4] Integration test: `test_cancellation_workflow_unchanged()` — end-to-end cancellation → no approval step → response delivered

### Implementation for User Story 4

- (No new implementation — gate condition already scoped to refund_request only. Tests verify scoping.)

**Checkpoint**: User Story 4 complete. Non-refund workflows unaffected. Tests passing.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge case handling, audit persistence, comprehensive integration

### Operator Interaction Edge Cases

- [X] T034 [P] Unit test: `test_invalid_input_retries_until_valid()` — operator enters invalid value → prompt repeats until valid approve/reject entered
- [X] T035 [P] Unit test: `test_empty_operator_note_allowed()` — operator can skip note entry (empty string or None both valid)
- [X] T036 [P] Unit test: `test_operator_note_preserved_exactly()` — arbitrary text in operator note is recorded as-is without trimming or modification

### Audit Log Persistence

- [X] T037 Unit test: `test_audit_log_jsonl_file_written()` — when `audit_log_path` set, each AuditLogEntry appended as JSONL line to file
- [X] T038 Unit test: `test_audit_log_jsonl_format_valid()` — JSONL entries are valid JSON and can be parsed back to dicts
- [X] T039 Unit test: `test_audit_log_get_audit_log_returns_copy()` — `HumanApprovalService.get_audit_log()` returns shallow copy; in-memory list not modified by caller

### End-to-End Integration

- [X] T040 Integration test: `test_end_to_end_refund_approve_with_audit_file()` — submit refund → approve → verify response and audit file both exist with correct data
- [X] T041 Integration test: `test_end_to_end_refund_reject_with_operator_note()` — submit refund → reject with note → verify audit file contains note
- [X] T042 Integration test: `test_multiple_decisions_audit_log_sequential()` — process multiple refund requests → verify audit log entries in order with unique entry_ids

### Documentation & CLI

- [X] T043 Update `README.md` in support-agent-python/: document `--audit-log` flag with example usage and JSONL format
- [X] T044 [P] Update QUICKSTART.md: add "Using Human Approval" section with example workflow

**Checkpoint**: Feature complete. All edge cases handled. Audit trail reliable. Documentation updated. Ready for release.

---

## Dependencies & Parallel Execution

### Dependency Graph

```
T002 (approval.py) ──────┬──────► T004 (approval_service.py)
                          ├──────► T006 (workflow_state.py)
                          ├──────► T008 (response_generator.py)
                          └──────► T009 (console_ui.py)

T003, T005 (exports) ◄── (depend on models/services created)

T007 (main_workflow gate) ◄── (depends on T002, T004, T006)

T008, T009 ◄── (depend on T002, T006)

T010, T011 (CLI) ◄── (depend on T004, T005)

Tests (T012+) ◄── (depend on all Phase 2 tasks)
```

### Recommended Parallel Execution

**Phase 2 can be executed as follows**:

1. **Wave 1** (parallel): T002 (approval.py), T006 (workflow_state.py)
2. **Wave 2** (parallel): T003, T004, T005 (exports + service, depends on T002)
3. **Wave 3** (parallel): T007, T008, T009 (workflow + response + UI, depend on T002/T004/T006)
4. **Wave 4** (parallel): T010, T011 (CLI, depend on T004/T005)

**Phase 3-6**: All test and implementation tasks within a story can run in parallel (noted with [P] label)

---

## Success Criteria Summary

| Criterion                                 | Verification                                |
| ----------------------------------------- | ------------------------------------------- |
| All refund requests trigger approval gate | Phase 6, T028-T033 tests pass               |
| Human operator can approve                | Phase 3, T013-T016 pass                     |
| Human operator can reject                 | Phase 4, T019-T024 pass                     |
| Human can override both directions        | Phase 5, T025-T027 pass                     |
| Non-refund requests unaffected            | Phase 6, T028-T033 pass                     |
| Audit log captures all decisions          | Phase 3-5 tests verify audit entry creation |
| Operator note optional but preserved      | Phase 7, T035-T036 pass                     |
| JSONL persistence works                   | Phase 7, T037-T042 pass                     |
| Edge cases handled                        | Phase 7, T034-T039 pass                     |

---

## Suggested MVP Scope

**Minimum Viable Product** = Phases 1-6 (feature complete with all user stories).

Phase 7 (Polish) can be deferred to a follow-up release if time-constrained.

**Estimated effort**:

- Phase 2 (Foundation): 4-6 hours
- Phases 3-6 (User Stories + Tests): 6-10 hours
- Phase 7 (Polish): 2-3 hours
- **Total**: 12-19 hours

