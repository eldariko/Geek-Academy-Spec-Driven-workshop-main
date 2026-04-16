# Tasks: Customer Support Agent

**Input**: Design documents from `/specs/001-customer-support-agent/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅  
**Tech Stack**: Python 3.11+, Microsoft Agent Framework (MAF), Microsoft Foundry  
**Project Root**: `support-agent-python/`

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[US#]**: Which user story this task belongs to
- Setup and Foundational phases have no story label

---

## Phase 1: Setup

**Purpose**: Project initialization, dependency declaration, skeleton directories

- [x] T001 Add MAF, azure-ai-inference, and pytest dependencies to support-agent-python/requirements.txt
- [x] T002 [P] Create support-agent-python/pytest.ini with testpaths, python_files, python_classes, python_functions settings
- [x] T003 [P] Create support-agent-python/tests/**init**.py and ensure tests/ directory exists
- [x] T004 [P] Create empty **init**.py files for app/agents/, app/models/, app/services/, app/workflows/ packages in support-agent-python/app/

**Checkpoint**: Project installs cleanly with `pip install -r requirements.txt`; pytest is runnable ✅

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and handbook loading that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete ✅

- [x] T005 Create CustomerRequest dataclass (raw_message, request_id, timestamp, customer_id, account_created_date, account_plan, detected_keywords, tone_indicators) in support-agent-python/app/models/request.py
- [x] T006 [P] Create ClassificationResult dataclass (request_id, classified_intent, confidence_score, reasoning, needs_policy_check, requires_customer_context, escalation_reason) in support-agent-python/app/models/classification.py
- [x] T007 [P] Create PolicyMatch and PolicyEvaluation dataclasses (rule_name, rule_category, matches, decision, rationale, handbook_reference; final_decision, evaluated_rules, clarification_needed_fields, escalation_reason) in support-agent-python/app/models/policy_match.py
- [x] T008 [P] Create SupportResponse dataclass (request_id, response_text, response_type, tone, handbook_citations, cited_policies, recommended_action, action_parameters, escalation_ticket_id) in support-agent-python/app/models/response.py
- [x] T009 [P] Create ClarificationRequest dataclass (request_id, missing_fields, questions, context_why_needed, max_retries=1) with format_for_console() method in support-agent-python/app/models/clarification.py
- [x] T010 [P] Create WorkflowState dataclass (request, classification, policy_evaluation, response, agent_log, error_occurred) with log_agent_step() method in support-agent-python/app/models/workflow_state.py
- [x] T011 [P] Export all model classes from support-agent-python/app/models/**init**.py
- [x] T012 Implement HandbookService class with load(), get_section(section_name), and search(query) methods reading support-agent-python/data/support_handbook.md in support-agent-python/app/services/handbook_service.py
- [x] T013 [P] Create FoundryClient wrapper around azure.ai.inference.ChatCompletionsClient with FOUNDRY_API_KEY env var loading and a complete(prompt) method in support-agent-python/app/services/foundry_client.py

**Checkpoint**: All model imports succeed; HandbookService loads handbook and returns non-empty sections; FoundryClient initializes with API key ✅

---

## Phase 3: User Story 1 — Simple Support Question Response (Priority: P1) 🎯 MVP

**Goal**: Handle general questions about the product by retrieving relevant info from the handbook and returning a policy-compliant, personalized answer

**Independent Test**: Run the app with "What's included in the Basic plan?" — system must return plan features from the handbook without speculation or unnecessary clarification prompts ✅

- [x] T014 [US1] Implement FastClassifier with regex/keyword rules (simple_question as default, refund/cancel/escalate keywords for detection) in support-agent-python/app/services/intent_classifier.py
- [x] T015 [P] [US1] Implement ClassifierAgent wrapping FastClassifier with classify(request: CustomerRequest) → ClassificationResult method in support-agent-python/app/agents/classifier.py
- [x] T016 [US1] Implement PolicyEngine skeleton with evaluate_simple_question(request, handbook_context) path that returns PolicyEvaluation(final_decision="APPROVE") in support-agent-python/app/services/policy_engine.py
- [x] T017 [US1] Implement ResponseAgent with generate(workflow_state: WorkflowState) → SupportResponse method handling "answer" response_type, including handbook_citations in support-agent-python/app/agents/response_generator.py
- [x] T018 [US1] Implement SupportRequestWorkflow.execute() sequential flow (Classifier → PolicyEngine → ResponseAgent) for simple_question intent in support-agent-python/app/workflows/main_workflow.py
- [x] T019 [US1] Implement Orchestrator.process(raw_message: str) → SupportResponse that initializes CustomerRequest, runs workflow, returns response in support-agent-python/app/orchestrator.py
- [x] T020 [US1] Update main.py interactive loop to accept console input, call Orchestrator.process(), and print response_text to console in support-agent-python/main.py

**Checkpoint**: `python main.py` starts console loop; entering "How do I export my data?" returns a policy-grounded answer; handbook is cited in output metadata ✅

---

## Phase 4: User Story 2 — Refund Request Processing (Priority: P1)

**Goal**: Evaluate refund requests against all five handbook criteria and return an APPROVE/DENY decision with policy-grounded explanation

**Independent Test**: Submit five refund scenarios (first month, double charge, service outage, forgot to cancel, already refunded this year) — system must match the correct handbook rule and return the right decision for each ✅

- [x] T021 [P] [US2] Implement FirstMonthRefundRule (account < 30 days, product unused) in support-agent-python/app/services/policy_engine.py
- [x] T022 [P] [US2] Implement BillingErrorRefundRule (double charge, wrong amount, charged after cancellation) in support-agent-python/app/services/policy_engine.py
- [x] T023 [P] [US2] Implement ServiceOutageRefundRule (outage recorded during billing period) in support-agent-python/app/services/policy_engine.py
- [x] T024 [P] [US2] Implement OnePerYearRule (previous goodwill refund within 12 months blocks new goodwill refund; does not block billing error refund) in support-agent-python/app/services/policy_engine.py
- [x] T025 [P] [US2] Implement ForgotToCancelRule (multi-month requests denied; most recent month offered as goodwill if polite) in support-agent-python/app/services/policy_engine.py
- [x] T026 [US2] Add refund keyword detection to FastClassifier ("refund", "money back", "charged", "overcharged", "double charge") in support-agent-python/app/services/intent_classifier.py
- [x] T027 [US2] Extend ResponseAgent to handle APPROVE and DENY decisions for refund_request intent: APPROVE includes 5-7 business day timeline; DENY explains which rule blocked it with handbook quote in support-agent-python/app/agents/response_generator.py
- [x] T028 [US2] Wire refund_request intent path in SupportRequestWorkflow — route to PolicyEngine refund evaluation, pass result to ResponseAgent in support-agent-python/app/workflows/main_workflow.py

**Checkpoint**: Each of the five refund scenarios from spec.md acceptance criteria produces the correct APPROVE/DENY decision; all decisions cite a handbook section ✅

---

## Phase 5: User Story 3 — Cancellation Request Processing (Priority: P1)

**Goal**: Process cancellation requests by confirming the timeline (immediate system, access until billing period end, 90-day data retention) without resistance

**Independent Test**: Submit "please cancel my account" — system must confirm cancellation timeline and mention data export option; submitting "should I cancel?" must answer the question without processing cancellation ✅

- [x] T029 [US3] Implement CancellationValidationRule that distinguishes explicit cancel intent from question ("should I cancel?") in support-agent-python/app/services/policy_engine.py
- [x] T030 [P] [US3] Add cancellation keyword detection to FastClassifier ("cancel", "terminate", "unsubscribe", "close account") and "should I cancel" advisory pattern in support-agent-python/app/services/intent_classifier.py
- [x] T031 [US3] Extend ResponseAgent with cancellation confirmation template: access until billing period end, 90-day data retention, link to self-serve export tool in support-agent-python/app/agents/response_generator.py
- [x] T032 [US3] Wire cancellation_request intent path in SupportRequestWorkflow — route to cancellation policy evaluation and confirmation response in support-agent-python/app/workflows/main_workflow.py

**Checkpoint**: "please cancel" returns confirmation with billing timeline; "should I cancel?" returns advisory answer; data export is mentioned in cancellation response ✅

---

## Phase 6: User Story 4 — Upset Customer Escalation (Priority: P2)

**Goal**: Detect escalation signals (explicit manager request, legal mentions, high frustration, repeated contacts) and route to human support instead of automated response

**Independent Test**: Submit "I want to talk to a manager NOW" and a message mentioning "lawyer" — both must return escalation notices; no automated policy decision must be made ✅

- [x] T033 [P] [US4] Implement EscalationDetector with all trigger patterns: explicit_manager_request ("manager", "supervisor"), legal_mention ("lawyer", "GDPR", "chargeback", "regulator"), abusive_tone (score threshold), billing_threshold (>$100), repeated_contacts (3+ same issue) in support-agent-python/app/agents/escalation_handler.py
- [x] T034 [P] [US4] Add escalation keyword detection to FastClassifier (manager, supervisor, lawyer, GDPR, ridiculous, outrage, etc.) mapping to escalation_needed intent in support-agent-python/app/services/intent_classifier.py
- [x] T035 [US4] Implement EscalationWorkflow that creates escalation context (full customer message, reason, priority) and returns EscalationNotice in support-agent-python/app/workflows/escalation_workflow.py
- [x] T036 [US4] Extend ResponseAgent with escalation_notice response type: acknowledges situation, confirms escalation, states 24-hour human follow-up without engaging with the underlying complaint in support-agent-python/app/agents/response_generator.py
- [x] T037 [US4] Wire escalation short-circuit into SupportRequestWorkflow: if ClassifierAgent returns escalation_needed skip PolicyEngine and call EscalationWorkflow; also trigger EscalationWorkflow if PolicyEvaluation returns ESCALATE in support-agent-python/app/workflows/main_workflow.py

**Checkpoint**: All four escalation triggers (manager request, legal mention, abuse, billing >$100) produce escalation_notice; workflow does not call PolicyEngine for escalation_needed classification ✅

---

---

## Phase 7: User Story 5 — Missing Information Clarification (Priority: P2)

**Goal**: Detect missing critical details, ask one targeted question, and resume processing after customer provides the information without looping back

**Independent Test**: Submit "I think I was charged twice but I'm not sure when" — system must ask for billing date and amount; after receiving answer, system must not ask again

- [ ] T038 [P] [US5] Implement MissingInfoDetector in PolicyEngine that identifies required fields per intent (refund: charge_date + amount; cancellation: nothing extra needed) and returns NEEDS_CLARIFICATION when fields are absent in support-agent-python/app/services/policy_engine.py
- [ ] T039 [US5] Implement ClarificationRequest builder that maps missing_fields to customer-friendly questions ("Which billing period are you referring to?" for charge_date) in support-agent-python/app/models/clarification.py
- [ ] T040 [US5] Extend ResponseAgent with clarification_request response type that formats multiple questions into a single numbered list and explains why info is needed in support-agent-python/app/agents/response_generator.py
- [ ] T041 [US5] Implement LLMClassifier fallback in intent_classifier.py using FoundryClient for ambiguous cases where FastClassifier confidence < 0.8 in support-agent-python/app/services/intent_classifier.py
- [ ] T042 [US5] Add clarification resume flow to SupportRequestWorkflow: when NEEDS_CLARIFICATION is returned, prompt user for input once, merge into original CustomerRequest context, and re-run from PolicyEngine (not from Classifier) in support-agent-python/app/workflows/main_workflow.py

**Checkpoint**: Vague refund request triggers clarification with specific questions; after user answers, workflow resumes without re-asking; LLM fallback fires for confidence < 0.8 cases

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Console UI, logging, environment configuration, developer tooling

- [ ] T043 [P] Update support-agent-python/app/console_ui.py to render response_type label, handbook_citations, recommended_action, and escalation info alongside response_text
- [ ] T044 [P] Add structured logging (request_id, agent name, decision, timestamp) to WorkflowState.log_agent_step() and wire it through all agents in support-agent-python/app/orchestrator.py
- [ ] T045 Add environment variable validation at startup (FOUNDRY_API_KEY required, helpful error if missing) in support-agent-python/main.py
- [ ] T046 [P] Add --test-mode CLI flag to main.py that processes all requests from support-agent-python/data/sample_requests.md and prints intent classification + decision for each

**Checkpoint**: Console output shows response type and policy citations; missing API key gives clear error; --test-mode runs all sample requests without error

---

## Dependencies (Story Completion Order)

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational: Models + HandbookService)
    ↓
Phase 3 (US1: Simple Questions) ← MVP: Deliver this first
    ↓
Phase 4 (US2: Refund) — depends on PolicyEngine from Phase 3
Phase 5 (US3: Cancellation) — depends on PolicyEngine from Phase 3
    ↓ (US2 and US3 can run in parallel after Phase 3)
Phase 6 (US4: Escalation) — depends on Classifier + ResponseAgent from Phase 3
Phase 7 (US5: Clarification) — depends on PolicyEngine (Phase 4) + LLM client (Phase 2)
    ↓
Phase 8 (Polish) — independent cross-cutting concerns
```

**Parallel execution within each story phase**: Tasks marked `[P]` within the same phase can run simultaneously (they touch different files).

---

## Implementation Strategy

**MVP Scope**: Complete Phase 1 + Phase 2 + Phase 3 (T001–T020)
After Phase 3, the app accepts questions and returns handbook-grounded answers — a working, demonstrable product.

**Increment 2**: Add Phase 4 + Phase 5 (T021–T032) — refund and cancellation flows
**Increment 3**: Add Phase 6 + Phase 7 (T033–T042) — escalation and clarification
**Increment 4**: Phase 8 (T043–T046) — polish and DX

---

## Summary

| Metric                            | Count   |
| --------------------------------- | ------- |
| **Total tasks**                   | 46      |
| **Phase 1 (Setup)**               | 4 tasks |
| **Phase 2 (Foundational)**        | 9 tasks |
| **Phase 3 (US1 — Simple Q)**      | 7 tasks |
| **Phase 4 (US2 — Refund)**        | 8 tasks |
| **Phase 5 (US3 — Cancellation)**  | 4 tasks |
| **Phase 6 (US4 — Escalation)**    | 5 tasks |
| **Phase 7 (US5 — Clarification)** | 5 tasks |
| **Phase 8 (Polish)**              | 4 tasks |
| **[P] parallelizable tasks**      | 26      |

**Format validation**: All 46 tasks include checkbox, sequential T-ID, [P] marker where applicable, [US#] label in story phases, and concrete file paths.
