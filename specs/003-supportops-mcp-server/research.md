# Research: SupportOps MCP Server

**Feature**: 003-supportops-mcp-server  
**Date**: 2026-04-26  
**Status**: Complete

## 1. Python MCP server transport choice

**Decision**: Use local Streamable HTTP transport for the SupportOps MCP server, exposed at `http://localhost:5058/mcp`.

**Rationale**: Lab requirements explicitly recommend Streamable HTTP and MCP Inspector validation before host integration. HTTP transport allows independent server startup, easy troubleshooting, and clean host/server boundaries.

**Alternatives considered**:
- STDIO transport: Rejected for this lab because Inspector validation and separate-process integration are less transparent.
- WebSocket transport: Rejected because workshop requirement and examples are centered on Streamable HTTP.

## 2. Policy ownership split

**Decision**: Keep policy evaluation in the host app (`support-agent-python`) and limit MCP to ground-truth data and action execution.

**Rationale**: The feature spec requires host orchestration and policy split. The host already has handbook-driven policy logic and intent classification, so this avoids duplicating policy rules in two places.

**Alternatives considered**:
- Move all policy logic into MCP: Rejected due to larger refactor and tighter coupling of business policy to tool layer.
- Duplicate policy in host and MCP: Rejected because rule drift risk is high.

## 3. MCP tool interface shape

**Decision**: Implement exactly three tools for this feature:
- `get_customer_context(email: string)`
- `create_ticket(customer_id: string, reason: string, priority: string)`
- `record_refund_event(customer_id: string, amount: float, reason: string)`

**Rationale**: Matches required capabilities while staying small and understandable. One tool provides data access, two tools provide concrete support actions.

**Alternatives considered**:
- One combined `process_support_action` tool: Rejected because it hides intent and weakens contract clarity.
- Additional tools (eligibility checker, account mutation): Deferred to future stretch scope.

## 4. Data source and persistence strategy

**Decision**: Use `mock-data-lab2/mock_customers.json` as read source for customer context; keep ticket and refund event records in-memory with optional append-to-file logging.

**Rationale**: Workshop scope prioritizes simplicity and deterministic local demos. File-backed customer data keeps sample scenarios stable and easy to inspect.

**Alternatives considered**:
- SQLite/PostgreSQL: Rejected as unnecessary operational complexity for workshop goals.
- Hardcoded customer dictionaries in code: Rejected because it duplicates provided mock data and is harder to maintain.

## 5. Error handling and host fallback behavior

**Decision**: Standardize MCP tool responses with explicit success/failure shape, machine-readable error code, and user-safe message hints for host fallback.

**Rationale**: The host must always return safe customer-facing output even when MCP calls fail. Explicit response contracts prevent ambiguous failures.

**Alternatives considered**:
- Throw-only error handling with no structured payload: Rejected because host fallback behavior becomes inconsistent.
- Silent failure with default values: Rejected due to policy correctness risks.

## 6. Testing and validation approach

**Decision**: Use two layers:
- Automated `pytest` tests for tool behavior and host orchestration decision points.
- Manual MCP Inspector validation for transport connectivity and live tool invocation.

**Rationale**: This directly maps to lab success criteria and catches both logic regressions and integration wiring issues.

**Alternatives considered**:
- Automated tests only: Rejected because transport configuration and inspector workflow are explicit acceptance criteria.
- Manual tests only: Rejected due to poor regression safety.
