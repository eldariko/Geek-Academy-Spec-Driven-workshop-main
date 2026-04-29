# Support Agent Python Architecture

## Overview

`support-agent-python` is a console-first support assistant that processes one customer message at a time through a host-orchestrated workflow.

Core goals:

- Classify intent quickly using deterministic rules, with optional LLM fallback for ambiguous inputs.
- Apply local policy logic from the support handbook.
- Enforce a human approval gate for refund decisions.
- Optionally call SupportOps MCP tools for customer context and operational actions.
- Produce a customer-facing response with safe fallbacks when dependencies fail.

Entry point: `main.py`.

## High-Level Flow

Runtime pipeline per request:

1. CLI accepts input (`interactive` mode or `--test-mode`).
2. `Orchestrator` creates a `CustomerRequest` and invokes `SupportRequestWorkflow.execute(...)`.
3. `ClassifierAgent` determines intent (`simple_question`, `refund_request`, `cancellation_request`, or `escalation_needed`).
4. Host workflow optionally enriches with MCP customer context (email extracted from message).
5. `PolicyEngine` evaluates rules and returns a decision (`APPROVE`, `DENY`, `NEEDS_CLARIFICATION`, `ESCALATE`).
6. For refund requests, `HumanApprovalService` collects operator `approve/reject` and logs audit events.
7. Host workflow optionally runs MCP action tools (`create_ticket`, `record_refund_event`) after policy and approval outcomes are known.
8. `ResponseAgent` builds the final `SupportResponse`.

## Component Structure

### Application Layer

- `main.py`
  - CLI arguments (`--test-mode`, `--use-llm`, `--audit-log`, `--mcp-endpoint`, `--mcp-timeout`).
  - Environment loading and dependency wiring.
  - Interactive loop and sample-request test execution.

- `app/orchestrator.py`
  - High-level facade used by `main.py`.
  - Creates request IDs and timestamps.
  - Delegates execution to workflow and returns `SupportResponse`.

- `app/workflows/main_workflow.py`
  - Main host orchestration logic.
  - Owns step ordering, clarification prompting, MCP lookup/action calls, and state transitions.

### Agent Layer

- `app/agents/classifier.py` (`ClassifierAgent`)
  - Uses `FastClassifier` first.
  - Optional LLM fallback if confidence is below threshold.

- `app/agents/response_generator.py` (`ResponseAgent`)
  - Maps workflow results to customer-safe response text.
  - Handles approval, denial, clarification, escalation, and fallback responses.

### Service Layer

- `app/services/intent_classifier.py`
  - `FastClassifier`: regex/keyword intent detection.
  - `LLMClassifier`: Azure Foundry fallback classifier.

- `app/services/policy_engine.py`
  - Refund/cancellation/simple-question policy evaluation.
  - Rule classes implement deterministic policy decisions.

- `app/services/approval_service.py`
  - Blocking console approval for refunds (`approve` or `reject`).
  - In-memory audit log + optional JSONL append (`--audit-log`).

- `app/services/foundry_client.py`
  - `FoundryClient`: Azure OpenAI chat completion wrapper.
  - `SupportOpsMcpClient`: Streamable HTTP MCP tool client.

- `app/services/handbook_service.py`
  - Handbook parsing and section retrieval used by policy/response logic.

### Models

Primary runtime dataclasses are in `app/models/`:

- `request.py` (`CustomerRequest`)
- `classification.py` (`ClassificationResult`)
- `policy_match.py` (`PolicyMatch`, `PolicyEvaluation`)
- `approval.py` (`Recommendation`, `HumanDecision`, `AuditLogEntry`)
- `workflow_state.py` (`WorkflowState`)
- `response.py` (`SupportResponse`)

Note: there is also a legacy flat `app/models.py` used by older lab scaffold code (`app/processor.py`). The current orchestrated runtime imports from the `app/models/` package.

## Decision and Control Ownership

- Host-owned decisions:
  - Workflow ordering and step execution.
  - Policy decision authority.
  - Human approval enforcement.
  - MCP tool call timing and error handling.

- Agent/service responsibilities:
  - Intent inference (`ClassifierAgent` + classifier services).
  - Policy evaluation (`PolicyEngine`).
  - Response synthesis (`ResponseAgent`).

This keeps governance and side effects in host code while making model-driven steps replaceable.

## External Integrations

### Azure OpenAI (optional)

Enabled with `--use-llm` and required env vars:

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT_NAME`

Used only as classifier fallback for low-confidence intent cases.

### SupportOps MCP (optional)

Configured by:

- CLI: `--mcp-endpoint`, `--mcp-timeout`
- Or env: `SUPPORT_OPS_MCP_ENDPOINT`

Tools invoked by host:

- `get_customer_context(email)`
- `create_ticket(customer_id, reason, priority)`
- `record_refund_event(customer_id, amount, reason)`

Failure mode: MCP errors are captured in `WorkflowState.mcp_errors`, and customer responses still degrade gracefully.

## State and Observability

- `WorkflowState` is the central per-request state container.
- `WorkflowState.log_agent_step(...)` records timestamped step logs.
- Logging uses Python `logging` with structured `extra` fields in key steps.
- Refund approval audit is persisted in-memory and optionally to JSONL.

## Error Handling Strategy

- Initialization errors (missing required config for enabled features) fail fast in `main.py`.
- Workflow execution wraps processing in `try/except`, marks `error_occurred`, and re-raises.
- Orchestrator has a final fallback response if workflow returns no response object.
- MCP invocation catches transport/execution errors and returns structured `{"ok": false, "error": ...}` payloads.

## Current Constraints and Notes

- Human approval is console-blocking and optimized for single-operator sessions.
- Clarification prompting is interactive-only (`stdin.isatty()`); non-interactive runs skip prompt turns.
- Policy rules are deterministic and intentionally transparent; they are not LLM-driven.
- `app/agent.py` and `app/processor.py` remain as earlier lab placeholders and are not part of the main orchestrated runtime path.

## Suggested Future Evolution

- Move interactive concerns (console prompts) behind interfaces for easier automation testing.
- Add explicit domain-level events for MCP operations and approval actions.
- Consolidate or remove legacy scaffold modules (`app/models.py`, `app/processor.py`) to reduce ambiguity.
- Add architecture decision records (ADRs) for policy ownership and HITL gating choices.
