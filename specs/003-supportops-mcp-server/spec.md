# Feature Specification: SupportOps MCP Server

**Feature Branch**: `003-create-feature-branch`  
**Created**: 2026-04-24  
**Status**: Draft  
**Input**: User description: "Create a feature specification for a SupportOps MCP Server with MCP data access and business action tools, host-led orchestration, and policy split."

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Personalize Support with Customer Context (Priority: P1)

As a support agent host workflow, I need customer account context before generating a final response so that the customer receives personalized and policy-consistent support.

**Why this priority**: Personalization and policy evaluation both depend on customer context. Without this, downstream action decisions can be incorrect.

**Independent Test**: Can be tested by submitting a request with a known customer email and verifying the host receives customer name, plan type, and refund history, then produces a personalized response.

**Acceptance Scenarios**:

1. **Given** a support request includes a known customer email, **When** the host requests customer context, **Then** the MCP returns customer name, plan type, and refund history for that customer
2. **Given** customer context is returned, **When** the host creates the final response, **Then** the response uses customer-specific details instead of a generic message
3. **Given** a customer email is unknown, **When** customer context is requested, **Then** the host receives a clear not-found outcome and continues with a safe fallback response

---

### User Story 2 - Execute Escalation as a Real Action (Priority: P1)

As a support operations workflow, I need escalation to create a ticket through MCP so that escalation is recorded as a concrete action, not only described in text.

**Why this priority**: This is the primary business-action outcome required by Lab 2 and proves host-to-MCP operational integration.

**Independent Test**: Can be tested by submitting an escalation-worthy request, confirming host policy evaluation indicates escalation, and verifying a ticket is created through MCP with returned ticket details.

**Acceptance Scenarios**:

1. **Given** host policy evaluation determines escalation is required, **When** the host requests ticket creation, **Then** MCP records a new ticket with customer identifier, reason, and priority
2. **Given** a ticket is created, **When** the host receives the result, **Then** the final customer response confirms that escalation was initiated
3. **Given** ticket creation fails, **When** MCP returns the error, **Then** the host returns a user-safe response and records the failure outcome for review

---

### User Story 3 - Record Refund Decisions as Ground-Truth Events (Priority: P2)

As a support workflow, I need approved refunds to be recorded as events through MCP so future policy checks can rely on complete refund history.

**Why this priority**: Recording refund outcomes closes the loop between decision and operational record and improves future policy accuracy.

**Independent Test**: Can be tested by processing a refund-approved case and verifying MCP records a refund event with customer identifier, amount, and reason.

**Acceptance Scenarios**:

1. **Given** host policy evaluation determines a refund should be granted, **When** the host calls refund event recording, **Then** MCP records a refund event with the provided customer identifier, amount, and reason
2. **Given** a refund event is successfully recorded, **When** a later request retrieves the same customer context, **Then** refund history includes the recorded event

---

### Edge Cases

- Customer context request uses an email with no matching customer record
- Ticket creation request includes an unsupported priority value
- Refund recording request includes zero or negative amount
- Host retries an action after timeout and MCP receives a duplicate request
- MCP is temporarily unavailable when the host needs customer data or action execution

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST provide a SupportOps MCP server that can be run and validated independently from the Lab 1 host app
- **FR-002**: System MUST expose a data-access capability `get_customer_context(email)` that returns customer name, plan type (Basic or Premium), and refund history for a known customer
- **FR-003**: System MUST use `mock_customers.json` as the source of customer context used by `get_customer_context(email)`
- **FR-004**: System MUST expose a business-action capability `create_ticket(customer_id, reason, priority)` that records escalation ticket creation and returns a ticket result to the host
- **FR-005**: System MUST expose a business-action capability `record_refund_event(customer_id, amount, reason)` that records successful refund outcomes and returns action confirmation to the host
- **FR-006**: Host application MUST remain the orchestrator of the end-to-end support workflow
- **FR-007**: Host application MUST evaluate policy against support handbook rules before deciding whether to trigger MCP action tools
- **FR-008**: MCP server MUST be the ground truth source for customer data retrieval and action execution outcomes
- **FR-009**: Workflow MUST follow this sequence for supported requests: classify request, fetch customer context, evaluate policy, execute required MCP action, generate final response
- **FR-010**: Final response MUST include personalized customer context when available, including at minimum customer name and plan-relevant phrasing
- **FR-011**: Escalation outcomes MUST invoke `create_ticket(...)` for execution rather than returning escalation as text-only intent
- **FR-012**: Refund-approved outcomes MUST invoke `record_refund_event(...)` so refund history remains current for future decisions
- **FR-013**: MCP responses MUST provide clear success and failure outcomes that allow the host to produce customer-safe fallback messaging
- **FR-014**: Feature scope MUST remain small and workshop-friendly while still demonstrating one data-access tool and one business-action tool in end-to-end flow

### Key Entities

- **Customer Context**: Operational customer profile used by host decisioning and response personalization; includes email, customer identifier, name, plan type, and refund history
- **Support Ticket**: Recorded escalation action containing ticket identifier, customer identifier, reason, priority, status, and creation timestamp
- **Refund Event**: Recorded refund action containing customer identifier, amount, reason, and event timestamp
- **Policy Decision**: Host-owned decision artifact that determines whether to escalate, refund, or provide standard response based on request plus context
- **Action Result**: MCP tool outcome object indicating success or failure and any returned identifiers/messages needed by the host

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: In MCP validation sessions, all required tools are discoverable and invocable through Streamable HTTP transport, including at least one successful data-access invocation and one successful action invocation
- **SC-002**: In end-to-end test runs using provided sample requests, 100% of responses for known customers include plan-aware personalization derived from retrieved customer context
- **SC-003**: For requests classified for escalation, 100% trigger a successful `create_ticket(...)` call or a recorded failure outcome; no escalation is delivered as text-only action intent
- **SC-004**: For approved refund outcomes, 100% trigger `record_refund_event(...)` and the recorded event is visible in subsequent customer context retrieval
- **SC-005**: End-to-end workflow demo completes with the sequence classify -> context lookup -> policy decision -> action execution -> final response for all targeted scenario types (general support, escalation, refund)

## Assumptions

- Lab 1 host components for classification, policy evaluation, and response generation already exist and are extended rather than replaced
- Support handbook rules remain authored and maintained by the host application, not by the MCP server
- Customer emails in sample support requests align with records in `mock_customers.json`
- `create_ticket(...)` and `record_refund_event(...)` are mock business actions suitable for workshop demonstration, not production billing/finance operations
- A single local environment is used for the demo, and both host and MCP server can access required sample data files
- Authentication, authorization, and multi-tenant separation are out of scope for this workshop feature
