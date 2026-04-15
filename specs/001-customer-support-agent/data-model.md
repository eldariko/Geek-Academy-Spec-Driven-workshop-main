# Data Model: Customer Support Agent

**Purpose**: Define entity structures, workflow messages, and data contracts  
**Date**: 2026-04-15  
**Scope**: MAF workflow serialization, inter-agent communication, persistence schemas

---

## Core Entities

### CustomerRequest

Represents the initial customer message and extracted context.

```python
@dataclass
class CustomerRequest:
    """Initial customer support request"""

    # Immutable input
    raw_message: str              # Original customer text
    timestamp: datetime
    request_id: str               # Unique ID for tracking

    # Optional context (if available)
    customer_id: Optional[str]    # Account identifier
    account_created_date: Optional[datetime]  # For 30-day window
    account_plan: Optional[str]   # "Basic" or "Premium"

    # Extracted from message (filled by preprocessing)
    detected_keywords: List[str]  # Values for keyword-based classification
    tone_indicators: Dict[str, float]  # {"angry": 0.8, "urgent": 0.6, ...}

    # Processing state
    intent_preliminary: Optional[str]  # From fast classifier
    intent_confidence: Optional[float]  # 0.0-1.0

    def __post_init__(self):
        """Validate request integrity"""
        assert len(self.raw_message) > 0
        assert len(self.request_id) > 0
```

### ClassificationResult

Output from Classifier Agent.

```python
@dataclass
class ClassificationResult:
    """Classifier Agent output: determined intent"""

    request_id: str
    classified_intent: str  # One of: "simple_question", "refund_request", "cancellation_request", "escalation_needed"
    confidence_score: float  # 0.0-1.0
    reasoning: str          # Why this classification (for logging)

    # Flags for downstream processing
    needs_policy_check: bool          # False only for escalation_needed
    requires_customer_context: bool   # True for refund/cancel (need account info)

    # Escalation signals (if applicable)
    escalation_reason: Optional[str]  # e.g., "explicit_manager_request", "legal_mention"

    @property
    def is_confident(self) -> bool:
        return self.confidence_score >= 0.85
```

### PolicyContext

Handbook information retrieved by Policy Agent.

```python
@dataclass
class PolicyMatch:
    """Single policy rule evaluation"""

    rule_name: str              # e.g., "first_month_refund", "double_charge_refund"
    rule_category: str          # "refund" | "cancellation" | "escalation"
    matches: bool               # Does this rule apply?
    decision: str               # "APPROVE", "DENY", "NEEDS_INFO", "ESCALATE"
    rationale: str              # Why this decision
    handbook_reference: str     # Quoted text from handbook

    def __repr__(self) -> str:
        return f"[{self.rule_category.upper()}] {self.rule_name}: {self.decision} — {self.rationale}"


@dataclass
class PolicyEvaluation:
    """Policy Agent output: all applicable rules evaluated"""

    request_id: str
    intent: str
    evaluated_rules: List[PolicyMatch]

    # Aggregated decision
    final_decision: str  # "APPROVE", "DENY", "NEEDS_CLARIFICATION", "ESCALATE"
    clarification_needed_fields: List[str]  # If NEEDS_CLARIFICATION
    escalation_reason: Optional[str]  # If ESCALATE

    # Response hints for next agent
    should_apologize: bool  # True for billing errors
    should_mention_timeline: bool  # True for refunds

    @property
    def is_approved(self) -> bool:
        return self.final_decision == "APPROVE"

    @property
    def is_denied_cleanly(self) -> bool:
        return self.final_decision == "DENY"

    @property
    def requires_escalation(self) -> bool:
        return self.final_decision == "ESCALATE"

    @property
    def needs_customer_input(self) -> bool:
        return self.final_decision == "NEEDS_CLARIFICATION"


@dataclass
class SupportResponse:
    """Response Agent output: final customer-facing response"""

    request_id: str
    response_text: str              # Main message to customer
    response_type: str              # "answer" | "clarification_request" | "escalation_notice"

    # Metadata for logging/audit
    tone: str                       # "professional", "empathetic", "firm"
    handbook_citations: List[str]   # Quoted policies applied
    cited_policies: List[str]       # Policy names (e.g., "first_month_refund")

    # Actions (if any)
    recommended_action: Optional[str]  # "issue_refund", "cancel_account", "create_ticket"
    action_parameters: Dict[str, Any]  # {"amount": 49.99, "reason": "service_outage"}

    # Escalation details (if applicable)
    escalation_ticket_id: Optional[str]
    escalation_reason: Optional[str]
    escalation_priority: Optional[str]  # "high", "normal"

    def __repr__(self) -> str:
        return f"[{self.response_type.upper()}] {self.response_text[:50]}..."
```

### ClarificationRequest

Data class for cases where more information is needed.

```python
@dataclass
class ClarificationRequest:
    """Response Agent requests customer to provide missing information"""

    request_id: str
    missing_fields: List[str]          # ["billing_date", "amount", "error_description"]
    questions: List[str]               # Customer-friendly questions to ask
    context_why_needed: str            # Explanation of why info is needed

    # Constraints
    max_retries: int = 1               # Ask once, consolidate next response
    timeout_seconds: Optional[int]     # None = wait indefinitely

    def format_for_console(self) -> str:
        """Format clarification request for console UI"""
        output = [self.context_why_needed, ""]
        for i, question in enumerate(self.questions, 1):
            output.append(f"{i}. {question}")
        return "\n".join(output)
```

### WorkflowState

Internal state maintained across agent invocations within a single workflow run.

```python
@dataclass
class WorkflowState:
    """Running state of the request through the workflow"""

    request: CustomerRequest
    classification: Optional[ClassificationResult] = None
    policy_evaluation: Optional[PolicyEvaluation] = None
    response: Optional[SupportResponse] = None

    # History for audit trail
    agent_log: List[str] = field(default_factory=list)  # Timestamps + agent outputs

    # Error state
    error_occurred: bool = False
    error_message: Optional[str] = None
    error_agent: Optional[str] = None  # Which agent raised the error

    def log_agent_step(self, agent_name: str, step_description: str, data: Any):
        """Record agent execution for audit"""
        entry = f"[{datetime.now().isoformat()}] {agent_name}: {step_description}"
        self.agent_log.append(entry)

    @property
    def is_escalable(self) -> bool:
        """Can this request be escalated to human?"""
        return not self.error_occurred or "escalation" in self.error_message.lower()
```

---

## Workflow Message Schemas

These are the exact payloads passed between agents.

### Classifier Input Schema

```json
{
	"request_id": "req_20260415_001",
	"raw_message": "I was charged twice last week and it was $50 each time. This is ridiculous!",
	"detected_keywords": ["charged", "twice", "$50"],
	"tone_indicators": { "angry": 0.7, "urgent": 0.8 },
	"intent_preliminary": "refund_request"
}
```

### Classifier Output Schema → Policy Agent Input

```json
{
	"request_id": "req_20260415_001",
	"classified_intent": "refund_request",
	"confidence_score": 0.92,
	"reasoning": "Message contains 'charged twice' + negative tone; refund_request classification",
	"needs_policy_check": true,
	"requires_customer_context": true,
	"escalation_reason": null
}
```

### Policy Agent Input Schema

```json
{
	"request_id": "req_20260415_001",
	"intent": "refund_request",
	"customer_context": {
		"customer_id": "cust_12345",
		"account_created_date": "2026-02-15",
		"refund_history_past_12m": [
			{ "date": "2026-03-10", "amount": 50.0, "reason": "goodwill_first_month" }
		]
	},
	"extracted_details": {
		"charge_amount": 50.0,
		"charge_date": "2026-04-08",
		"charge_count": 2
	},
	"handbook_sections": ["Refunds", "Billing Errors"]
}
```

### Policy Agent Output Schema → Response Agent Input

```json
{
	"request_id": "req_20260415_001",
	"intent": "refund_request",
	"evaluated_rules": [
		{
			"rule_name": "double_charge_refund",
			"rule_category": "refund",
			"matches": true,
			"decision": "APPROVE",
			"rationale": "Obvious billing error on our side; double charge detected",
			"handbook_reference": "Obvious billing error on our side (double charge, wrong amount, charged after cancellation). Refund and apologize, no drama."
		},
		{
			"rule_name": "one_per_year_rule",
			"rule_category": "refund",
			"matches": false,
			"decision": "N/A",
			"rationale": "Previous goodwill refund was within year, but this is BILLING ERROR category (not goodwill)",
			"handbook_reference": "Customer has already had a refund within the past year. Our informal rule is one goodwill refund per customer per year."
		}
	],
	"final_decision": "APPROVE",
	"should_apologize": true,
	"should_mention_timeline": true,
	"escalation_reason": null
}
```

### Response Agent Input Schema

```json
{
	"request_id": "req_20260415_001",
	"original_request": "I was charged twice last week and it was $50 each time. This is ridiculous!",
	"classification": {
		"intent": "refund_request",
		"confidence": 0.92
	},
	"policy_eval": {
		"final_decision": "APPROVE",
		"cited_policies": ["double_charge_refund"],
		"should_apologize": true,
		"should_mention_timeline": true
	}
}
```

### Response Agent Output Schema

```json
{
	"request_id": "req_20260415_001",
	"response_text": "I sincerely apologize for the billing error. I can see you were incorrectly charged twice on April 8th for $50 each. This is absolutely our mistake. I've processed a refund of $50 back to your original payment method. You should see it within 5-7 business days depending on your card issuer. I've also reviewed your account to ensure this doesn't happen again. Thank you for bringing this to our attention.",
	"response_type": "answer",
	"tone": "empathetic",
	"handbook_citations": [
		"Obvious billing error on our side (double charge, wrong amount, charged after cancellation). Refund and apologize, no drama."
	],
	"cited_policies": ["double_charge_refund"],
	"recommended_action": "issue_refund",
	"action_parameters": {
		"amount": 50.0,
		"reason": "billing_error_double_charge",
		"customer_id": "cust_12345"
	},
	"escalation_ticket_id": null,
	"escalation_reason": null
}
```

---

## Entity Relationships

```
CustomerRequest (input)
    ↓ [passes to Classifier]
ClassificationResult
    ↓ [passes to PolicyAgent if not escalation]
PolicyEvaluation
    ├─ APPROVE / DENY → [passes to ResponseAgent]
    ├─ NEEDS_CLARIFICATION → [ClarificationRequest to customer]
    └─ ESCALATE → [EscalationTicket created]
        ↓ [passes to ResponseAgent]
SupportResponse (output to customer)
```

---

## Persistence Schema (Future / Lab 2)

For optional human-in-the-loop or audit trails:

```python
@dataclass
class TicketRecord:
    """Persisted support ticket (for Lab 2 with database)"""

    ticket_id: str
    customer_id: str
    created_at: datetime

    original_request: str
    initial_classification: str
    policy_outcomes: List[str]
    final_response: str

    action_taken: Optional[str]        # "refund_issued", "cancelled", "escalated"
    status: str                        # "resolved", "escalated", "awaiting_customer"

    # Human interactions (Lab 2 feature)
    human_review_requested: bool
    reviewed_by: Optional[str]         # Support agent name
    review_notes: Optional[str]

    # Metrics
    resolution_time_seconds: int
    customer_satisfaction: Optional[int]  # 1-5 rating (if collected)
```

---

## Summary

All data models are:

- ✅ Immutable where appropriate (input data)
- ✅ Dataclass-based for serialization
- ✅ Auditable (all policies traced, all decisions logged)
- ✅ Workflow-friendly (each agent's output matches next agent's input schema)
- ✅ Type-safe (can be validated at runtime)
- ✅ Grounded in specification (entity names match spec.md + handbook)
