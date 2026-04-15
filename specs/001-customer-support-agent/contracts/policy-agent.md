# Policy Agent Contract

**Purpose**: Evaluate customer request against support handbook policies  
**Pattern**: Decision engine (applies rules, returns structured decision)  
**Framework**: Microsoft Agent Framework (MAF)  
**Dependency**: Handbook service (loads support_handbook.md)

## Input Schema

```python
@dataclass
class PolicyAgentInput:
    request_id: str             # From classifier
    intent: str                 # From classifier (simple_question, refund_request, cancellation_request)
    original_message: str       # For context

    # Customer context (optional, needed for refund/cancel decisions)
    customer_id: Optional[str]
    account_created_date: Optional[datetime]

    # Request-specific details (extracted from message or provided)
    charge_amount: Optional[float]      # For refund decisions
    charge_date: Optional[datetime]
    reason_stated: Optional[str]        # "I forgot to cancel", "billing error", etc.

    # Request history (for policy checks)
    refund_history_past_12m: List[Dict]  # [{amount, date, reason}, ...]
    interaction_count_this_month: int    # For escalation trigger
```

Example:

```json
{
	"request_id": "req_20260415_001",
	"intent": "refund_request",
	"original_message": "I was charged twice last week",
	"customer_id": "cust_12345",
	"account_created_date": "2026-02-15",
	"charge_amount": 50.0,
	"charge_date": "2026-04-08",
	"refund_history_past_12m": [],
	"interaction_count_this_month": 1
}
```

## Output Schema

```python
@dataclass
class PolicyAgentOutput:
    request_id: str             # Echo input request_id
    intent: str                 # Echo input intent

    # Rule evaluation results
    rules_evaluated: List[RuleEvaluation]  # All applicable rules + results

    # Aggregated decision
    final_decision: str  # APPROVE, DENY, NEEDS_CLARIFICATION, ESCALATE

    # If NEEDS_CLARIFICATION
    missing_fields: Optional[List[str]]
    clarification_questions: Optional[List[str]]

    # If decision is DENY or requires explanation
    denial_reason: Optional[str]

    # Response hints for Response Agent
    should_apologize: bool          # True for billing errors
    should_mention_timeline: bool   # True for refunds

    # If ESCALATE
    escalation_reason: Optional[str]
    escalation_priority: Optional[str]  # "high", "normal"
```

Example:

```json
{
	"request_id": "req_20260415_001",
	"intent": "refund_request",
	"rules_evaluated": [
		{
			"rule_name": "double_charge_refund",
			"matches": true,
			"decision": "APPROVE",
			"handbook_ref": "Obvious billing error on our side (double charge, wrong amount, charged after cancellation). Refund and apologize, no drama."
		}
	],
	"final_decision": "APPROVE",
	"should_apologize": true,
	"should_mention_timeline": true,
	"escalation_reason": null
}
```

## Contract Guarantees

✅ **final_decision is always set** (never null: APPROVE | DENY | NEEDS_CLARIFICATION | ESCALATE)  
✅ **All policy citations come from handbook** (no invented rules)  
✅ **If NEEDS_CLARIFICATION, missing_fields list is provided**  
✅ **If ESCALATE, escalation_reason explains why**  
✅ **If DENY, denial_reason explains policy violation**  
✅ **All decisions are auditable** (rules_evaluated shows all matches)

## Policy Rules Evaluated

### For refund_request intent:

1. **FirstMonthRefundRule** — Within 30 days, hasn't used product → APPROVE
2. **ServiceOutageRefundRule** — Outage during billing period → APPROVE
3. **BillingErrorRefundRule** — Double charge, wrong amount, charged after cancel → APPROVE
4. **OnePerYearRule** — Already had goodwill refund in past year → DENY (except billing error)
5. **ForgotToCancelRule** — Multiple months decline, recent still goodwill → APPROVE (most recent only)

### For cancellation_request intent:

1. **CancellationValidationRule** — Is intent truly cancellation or asking question? → APPROVE if clear
2. **DataExportRule** — Customer asked about data → Include export tool mention

### For simple_question intent:

1. **ContextualAnswerRule** → Handbook lookup + provide answer

### For escalation_needed intent:

1. **EscalationTriggerRule** → Already triggered; escalate to human

## Error Handling

- If handbook cannot be loaded → ESCALATE with reason "Internal error: handbook unavailable"
- If customer context missing for refund evaluation → NEEDS_CLARIFICATION
- If policy conflict (multiple rules disagree) → ESCALATE for senior decision
- If unknown intent → ESCALATE

## Implementation Location

`app/services/policy_engine.py::PolicyEngine`  
`app/services/handbook_service.py::HandbookService`

---

## Test Cases

| Scenario                                           | Expected Decision   | Reason                              |
| -------------------------------------------------- | ------------------- | ----------------------------------- |
| Double charge, account 3 months old                | APPROVE             | Billing error rule                  |
| Service outage on day 5, refund requested on day 6 | APPROVE             | Service outage rule                 |
| Forgot to cancel, 8 months in, 2nd refund request  | DENY                | One-per-year rule + multiple months |
| Forgot to cancel, 1st month, polite request        | APPROVE             | First month goodwill                |
| "How do I export?" + cancel request                | APPROVE (cancel)    | Clear intent, provide export URL    |
| "Should I cancel?" (asking question)               | NEEDS_CLARIFICATION | Not explicit cancel                 |
| Customer 4th contact same issue this month         | ESCALATE            | Contact frequency trigger           |
| >$100 billing dispute                              | ESCALATE            | Monetary threshold                  |
| Missing account creation date for 30-day check     | NEEDS_CLARIFICATION | Cannot evaluate window              |
