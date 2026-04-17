---
agents:
  - speckit.git.commit
---

# Implementation Plan: Customer Support Agent

**Branch**: `001-customer-support-agent` | **Date**: 2026-04-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-customer-support-agent/spec.md`

## Summary

Build a Python console application that intelligently routes customer support requests to specialized agents using Microsoft Agent Framework workflows. The system classifies requests (simple question, refund, cancellation, escalation), retrieves policy-specific information from the support handbook, and provides unified responses that follow company rules without inventing policies. Multi-agent architecture ensures policy compliance and appropriate escalation.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**:

- Microsoft Agent Framework (MAF) for multi-agent workflows
- Azure OpenAI (via Azure AI Inference / Foundry endpoint) as LLM provider
- Standard library: pathlib, json, logging, re for text processing

**Storage**: File-based (local YAML/JSON for handbook and sample requests; no database)  
**Testing**: pytest with unittest for unit tests, integration tests for workflow  
**Target Platform**: Windows PowerShell, macOS/Linux console (command-line)
**Project Type**: Console CLI application with multi-agent orchestration  
**Performance Goals**: <2 seconds response time per request (includes LLM inference)
**Constraints**: Offline handbook data lookup only; no external API calls except to Azure OpenAI LLM  
**Scale/Scope**: Single request processing per session; handbook-driven decision making; ~500 LOC for Phase 1

## Constitution Check

✅ **GATE: PASS** - No constitution constraints defined yet. Feature scope (console CLI with file-based data, single-request processing, no database) maintains simplicity principle.

**Note**: Constitution will be created in initialization phase if organizational principles are defined.

## Project Structure

### Documentation (this feature)

```text
specs/001-customer-support-agent/
├── plan.md              # This file (current output)
├── research.md          # Phase 0: MAF agents best practices, Foundry integration patterns (NEXT)
├── data-model.md        # Phase 1: State structures, workflow schemas, data contracts
├── quickstart.md        # Phase 1: Agent setup guide, workflow initialization
├── contracts/           # Phase 1: Agent interface specs, message schemas
│   ├── classifier-agent.md
│   ├── policy-agent.md
│   ├── response-agent.md
│   └── escalation-agent.md
└── checklists/
    └── requirements.md  # Quality validation checklist
```

### Source Code (support-agent-python)

```text
support-agent-python/
├── main.py                          # Entry point: CLI, request input, response output
├── requirements.txt                 # Python dependencies
├── pytest.ini                       # Test configuration
│
├── app/
│   ├── __init__.py
│   ├── orchestrator.py              # Request → Workflow coordinator
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── classifier.py            # Intent classification (Q/refund/cancel/escalate)
│   │   ├── policy_lookup.py         # Handbook context retrieval
│   │   ├── response_generator.py    # Unified response composition
│   │   └── escalation_handler.py    # Escalation detection & routing
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── request.py               # CustomerRequest entity
│   │   ├── response.py              # SupportResponse entity
│   │   ├── policy_match.py          # PolicyMatch entity
│   │   └── clarification.py         # ClarificationRequest entity
│   │
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── main_workflow.py         # MAF workflow definition: classify → lookup → respond
│   │   └── escalation_workflow.py   # Alternative path for escalations
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── handbook_service.py      # Load & search support_handbook.md
│   │   ├── intent_classifier.py     # Classification logic
│   │   └── policy_engine.py         # Apply refund/cancel/escalation rules
│   │
│   ├── console_ui.py                # Console rendering (existing)
│   ├── models.py                    # (existing, may be refactored)
│   ├── processor.py                 # (existing, will integrate with orchestrator)
│   ├── renderer.py                  # Response formatting (existing, reuse)
│   └── agent.py                     # (existing, may be deprecated/refactored)
│
├── data/
│   ├── support_handbook.md          # (existing, used by handbook_service)
│   └── sample_requests.md           # (existing, for testing)
│
└── tests/
    ├── __init__.py
    ├── test_classifier.py           # Intent classification tests
    ├── test_policy_engine.py        # Refund/cancel/escalation rules
    ├── test_handbook_lookup.py      # Context retrieval tests
    ├── test_response_generator.py   # Response composition tests
    ├── test_workflows/
    │   ├── test_main_workflow.py    # End-to-end workflow tests
    │   └── test_escalation_workflow.py
    └── fixtures/
        ├── sample_requests.json     # Test request payloads
        └── expected_responses.json  # Expected output for validation
```

**Structure Decision**: Single-application structure with modular agent separation. Each agent is a distinct module under `app/agents/` with its own business logic isolated. The `workflows/` package contains MAF workflow definitions that orchestrate agent execution. The `services/` layer handles cross-cutting concerns (handbook lookup, business rule evaluation). This separation ensures:

- Each agent can be tested independently
- Business rules are centralized and reusable
- MAF workflows remain clean and declarative
- Console I/O is decoupled from agent logic

## Design Principles (Phase 1 Goals)

### Agent Architecture

1. **Classifier Agent**: Analyzes raw customer message and determines intent
   - Input: customer request text, minimal context
   - Output: intent classification (simple_question, refund_request, cancellation_request, escalation_needed)
   - Error case: ambiguous intent → clarification request

2. **Policy Agent**: Retrieves handbook information and evaluates eligibility
   - Input: classified intent, customer context, extracted details
   - Output: applicable policies, eligibility evaluation, missing information
   - Decision points: refund approval/denial, escalation criteria met

3. **Response Agent**: Composes the final unified customer response
   - Input: policy evaluation, handbook citations, customer details
   - Output: single coherent response (not multiple internal handoffs)
   - Constraint: All statements must be grounded in handbook or policy engine

4. **Escalation Handler** (conditional): Routes to human when needed
   - Input: escalation signals or unresolvable cases
   - Output: escalation ticket with full context
   - Triggers: explicit manager request, legal mentions, 3+ unresolved same-issue contacts, >$100 billing dispute

### Workflow Flow (MAF)

```
Customer Request (text)
        ↓
[Classifier Agent] → Intent + Confidence
        ↓
    [Decision Point]
    ├─ Simple Question → [Policy Agent]
    ├─ Refund Request → [Policy Agent (refund rules)]
    ├─ Cancellation → [Policy Agent (cancel rules)]
    └─ Escalation Signal → [Escalation Handler]
        ↓
[Policy Agent] → Handbook context + Eligibility
        ↓
    [Decision Point]
    ├─ Complete info → [Response Agent]
    ├─ Missing info → [Ask Clarification] → (await customer reply)
    └─ Escalation → [Escalation Handler]
        ↓
[Response Agent] → Unified Customer Response
        ↓
Output to Console
```

### Data Flow

- **Request Input**: Console UI collects customer message + optional context (account info, billing dates)
- **Processing**: Flows through workflow via MAF agents
- **Policy Lookups**: Handbook_service provides O(1) policy access via indexed sections
- **State Management**: Each request is stateless within a session (no persistence between invocations)
- **Response Output**: Single unified message back to customer

## Phase 0: Research Tasks

_Research to be completed before implementation_

### Task 1: MAF Agent Patterns

- Research Microsoft Agent Framework multi-agent workflow syntax
- Research best practices for agent communication in MAF
- Research MAF state management between agent steps
- Decision needed: Fan-out vs. sequential agent execution

### Task 2: Azure OpenAI Integration

- Research Azure OpenAI/Foundry authentication and configuration
- Research token counting for refund/escalation decision prompts
- Research latency expectations for Azure OpenAI requests
- Decision needed: Prompt optimization for <2s response goal

### Task 3: Classification Strategy

- Research NLP techniques for intent classification without heavy dependencies
- Research handling of ambiguous/borderline cases
- Research one-shot vs. few-shot prompting for classification
- Decision needed: Rule-based vs. LLM-based classifier

### Task 4: Policy Engine Design

- Research handling of temporal policies (30-day window for refunds)
- Research best practices for rule engine state
- Research conflict resolution (multiple matching rules)
- Decision needed: Rete algorithm vs. simpler cascade evaluation

## Phase 1: Design Artifacts (Output)

After research, create:

1. **research.md** — Findings + decisions from Phase 0 tasks
2. **data-model.md** — Entity structures, state schemas, workflow messages
3. **contracts/** — Agent interface contracts, message format specs
4. **quickstart.md** — Setup guide, MAF initialization, first workflow run
5. **Agent-specific context** — Update copilot instructions with MAF patterns discovered
