# Tasks: SupportOps MCP Server (Python)

**Input**: Design documents from `/specs/003-supportops-mcp-server/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include `pytest` coverage for MCP tool validation and host orchestration behavior, plus one manual MCP Inspector checkpoint per quickstart.

**Organization**: Tasks are grouped by user story for independent implementation/testing, while clearly separating MCP server work in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/` and host work in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Each task includes exact file path(s)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare both Python projects and baseline scaffolding for MCP + host integration.

- [x] T001 Confirm Python MCP dependencies in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/requirements.txt`
- [x] T002 Create MCP package folders and `__init__.py` files in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/tools/`, `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/models/`, and `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/services/`
- [x] T003 [P] Add MCP endpoint/runtime configuration constants in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/config.py`
- [x] T004 [P] Add host MCP client configuration placeholders in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/main.py`
- [x] T005 [P] Add test package skeletons in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/tests/unit/` and `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/tests/integration/`

---

## Phase 2: Foundational Data Models & Contract Validation (Blocking)

**Purpose**: Implement shared schemas and strict validation rules before story-level tool behavior.

**⚠️ CRITICAL**: No user story work starts until this phase is complete.

- [x] T006 Implement MCP domain dataclasses (`CustomerContext`, `RefundHistoryItem`, `SupportTicket`, `RefundEvent`) in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/models/domain.py`
- [x] T007 Implement MCP response envelope models (`ToolSuccess`, `ToolError`, `ActionResult`) in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/models/results.py`
- [x] T008 Implement contract-first validators for `email` normalization + required/non-empty checks in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/services/validators.py`
- [x] T009 Implement contract-first enum validators for `plan_type` (`Basic|Premium`) and `priority` (`low|medium|high|urgent`) in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/services/validators.py`
- [x] T010 Implement contract-first numeric validator enforcing `amount > 0` in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/services/validators.py`
- [x] T011 [P] Add unit tests for validation rules (`email`, `plan_type`, `priority`, `amount`) in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/tests/unit/test_validators.py`
- [x] T012 [P] Implement customer data loader service over `Geek-Academy-Spec-Driven-workshop-main/mock-data-lab2/mock_customers.json` in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/services/customer_store.py`
- [x] T013 [P] Add unit tests for customer store parsing and enum constraints in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/tests/unit/test_customer_store.py`
- [x] T014 Implement common MCP error mapping (`INVALID_ARGUMENT`, `CUSTOMER_NOT_FOUND`, `INVALID_PRIORITY`, `INVALID_AMOUNT`, `INTERNAL_ERROR`) in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/services/error_mapper.py`

**Checkpoint**: Foundational schema/validator layer complete; user stories can begin.

---

## Phase 3: User Story 1 - Personalize Support with Customer Context (Priority: P1) 🎯 MVP

**Goal**: Host retrieves customer context from MCP and personalizes responses using returned name/plan/refund history.

**Independent Test**: Run host flow with known and unknown customer emails; confirm `get_customer_context` drives personalized output and fallback behavior.

### Tests for User Story 1

- [x] T015 [P] [US1] Add contract tests for `get_customer_context` success/failure payloads in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/tests/unit/test_get_customer_context_contract.py`
- [x] T016 [P] [US1] Add host integration tests for personalization + unknown-customer fallback in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/tests/integration/test_customer_context_integration.py`

### Tool Implementation (MCP Server)

- [x] T017 [US1] Implement `get_customer_context(email)` handler in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/tools/get_customer_context.py`
- [x] T018 [US1] Register `get_customer_context` tool with Streamable HTTP MCP server startup in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/main.py`

### Integration (Host)

- [x] T019 [US1] Implement host MCP client method for customer context lookup in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/app/services/foundry_client.py`
- [x] T020 [US1] Update workflow orchestration to call context lookup before policy evaluation in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/app/workflows/main_workflow.py`
- [x] T021 [US1] Update response generation to include customer name + plan-aware messaging in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/app/agents/response_generator.py`

**Checkpoint**: US1 is independently testable and delivers personalized responses.

---

## Phase 4: User Story 2 - Execute Escalation as a Real Action (Priority: P1)

**Goal**: Escalation policy outcomes trigger real ticket creation via MCP instead of text-only escalation messages.

**Independent Test**: Run escalation scenario and confirm host calls `create_ticket`, receives ticket id, and returns escalation response with action result.

### Tests for User Story 2

- [x] T022 [P] [US2] Add contract tests for `create_ticket` input validation and response shape in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/tests/unit/test_create_ticket_contract.py`
- [x] T023 [P] [US2] Add host integration tests verifying escalation invokes MCP action and handles tool failure fallback in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/tests/integration/test_escalation_ticket_integration.py`

### Tool Implementation (MCP Server)

- [x] T024 [US2] Implement in-memory ticket action service in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/services/ticket_service.py`
- [x] T025 [US2] Implement `create_ticket(customer_id, reason, priority)` tool handler with enum validation in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/tools/create_ticket.py`
- [x] T026 [US2] Register `create_ticket` tool in MCP server startup in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/main.py`

### Integration (Host)

- [x] T027 [US2] Implement host MCP client method for ticket creation in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/app/services/foundry_client.py`
- [x] T028 [US2] Wire escalation branch to call `create_ticket` and persist tool result in workflow state in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/app/workflows/main_workflow.py`
- [x] T029 [US2] Update escalation renderer to include created ticket reference in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/app/renderer.py`

**Checkpoint**: US2 is independently testable and always executes escalation as an action call.

---

## Phase 5: User Story 3 - Record Refund Decisions as Ground-Truth Events (Priority: P2)

**Goal**: Approved refunds create durable refund events in MCP so future context retrieval includes new history.

**Independent Test**: Run approved-refund scenario, confirm `record_refund_event` is called, then verify subsequent context lookup contains appended event.

### Tests for User Story 3

- [x] T030 [P] [US3] Add contract tests for `record_refund_event` (`amount > 0`, customer exists, non-empty reason) in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/tests/unit/test_record_refund_event_contract.py`
- [x] T031 [P] [US3] Add host integration tests for refund event recording and replay in later context lookups in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/tests/integration/test_refund_event_integration.py`

### Tool Implementation (MCP Server)

- [x] T032 [US3] Implement in-memory refund event service with append/read behavior in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/services/refund_service.py`
- [x] T033 [US3] Implement `record_refund_event(customer_id, amount, reason)` handler in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/app/tools/record_refund_event.py`
- [x] T034 [US3] Register `record_refund_event` tool in MCP server startup in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/main.py`

### Integration (Host)

- [x] T035 [US3] Implement host MCP client method for refund event recording in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/app/services/foundry_client.py`
- [x] T036 [US3] Wire refund-approved policy path to call MCP event recorder before final response in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/app/workflows/main_workflow.py`
- [x] T037 [US3] Update refund response copy to confirm recorded action outcome in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/app/agents/response_generator.py`

**Checkpoint**: US3 is independently testable and updates future context via recorded refund history.

---

## Phase 6: Integration & Validation (Cross-Cutting)

**Purpose**: Verify transport/tool registration and finalize end-to-end behavior.

- [x] T038 Add MCP server run instructions and tool list in `Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python/README.md`
- [x] T039 [P] Add host MCP endpoint configuration + fallback documentation in `Geek-Academy-Spec-Driven-workshop-main/support-agent-python/README.md`
- [ ] T040 Execute manual MCP Inspector validation checkpoint (Streamable HTTP connect, tool discovery, one data call + one action call) and document results in `Geek-Academy-Spec-Driven-workshop-main/specs/003-supportops-mcp-server/quickstart.md`
- [x] T041 Run end-to-end scenario matrix (personalization, escalation action, refund recording) and capture outcomes in `Geek-Academy-Spec-Driven-workshop-main/specs/003-supportops-mcp-server/quickstart.md`
- [x] T042 Run full Python tests for both projects and record command/results in `Geek-Academy-Spec-Driven-workshop-main/specs/003-supportops-mcp-server/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Starts immediately.
- **Phase 2 (Foundational Data Models & Validation)**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2; MVP path starts here.
- **Phase 4 (US2)**: Depends on Phase 2; can proceed after US1 or in parallel with US1 if team capacity allows.
- **Phase 5 (US3)**: Depends on Phase 2; can proceed after US1 or in parallel with US2.
- **Phase 6 (Integration & Validation)**: Depends on completion of desired user stories.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories once foundational phase is done.
- **US2 (P1)**: Uses shared MCP client/workflow files but is independently testable from US1.
- **US3 (P2)**: Uses shared MCP client/workflow files but is independently testable from US1/US2.

### Within Each User Story

- Contract/integration tests before implementation tasks.
- MCP tool/service implementation before host integration wiring.
- Host workflow wiring before response wording refinements.

### Parallel Opportunities

- Phase 1 tasks marked `[P]` can run in parallel.
- In Phase 2, T011-T013 can run in parallel after base models/validators exist.
- In each story, test tasks marked `[P]` can run in parallel.
- MCP server tasks and host tasks can be split across team members once contracts are fixed.

---

## Parallel Example: User Story 1

```bash
# Run US1 test tasks in parallel:
Task: T015 [US1] in support-ops-mcp-python/tests/unit/test_get_customer_context_contract.py
Task: T016 [US1] in support-agent-python/tests/integration/test_customer_context_integration.py

# After T017, MCP and host can proceed in parallel:
Task: T018 [US1] tool registration in support-ops-mcp-python/main.py
Task: T019 [US1] host MCP client in support-agent-python/app/services/foundry_client.py
```

## Parallel Example: User Story 2

```bash
# Run US2 tests in parallel:
Task: T022 [US2] in support-ops-mcp-python/tests/unit/test_create_ticket_contract.py
Task: T023 [US2] in support-agent-python/tests/integration/test_escalation_ticket_integration.py

# Split implementation across projects:
Task: T024-T026 [US2] in support-ops-mcp-python/
Task: T027-T029 [US2] in support-agent-python/
```

## Parallel Example: User Story 3

```bash
# Run US3 tests in parallel:
Task: T030 [US3] in support-ops-mcp-python/tests/unit/test_record_refund_event_contract.py
Task: T031 [US3] in support-agent-python/tests/integration/test_refund_event_integration.py

# Split implementation across projects:
Task: T032-T034 [US3] in support-ops-mcp-python/
Task: T035-T037 [US3] in support-agent-python/
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 (US1) end-to-end.
3. Validate personalization and fallback behavior before proceeding.

### Incremental Delivery

1. Add US2 to convert escalation into real MCP action execution.
2. Add US3 to persist refund outcomes and enrich future context.
3. Finish with Phase 6 validation checkpoints (Inspector + scenario matrix + full tests).

### Team Strategy

1. Shared effort on Setup/Foundational phases.
2. Split by project boundary afterward:
   - Developer A: `support-ops-mcp-python/`
   - Developer B: `support-agent-python/`
3. Rejoin for integration checkpoints and manual Inspector validation.

---

## Notes

- `[P]` tasks are parallel-safe by file ownership or explicit dependency ordering.
- Every user story remains independently testable.
- Contract-first validation tasks enforce `amount > 0`, strict enums, and required fields before tool handlers are finalized.
- Manual MCP Inspector validation is mandatory before marking the feature complete.
