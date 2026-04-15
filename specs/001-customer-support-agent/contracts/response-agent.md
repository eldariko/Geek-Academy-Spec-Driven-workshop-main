# Response Agent Contract

**Purpose**: Compose unified customer-facing response based on classification and policy decisions  
**Pattern**: Generation engine (creates human-readable output)  
**Framework**: Microsoft Agent Framework (MAF)

## Input Schema

```python
@dataclass
class ResponseAgentInput:
    request_id: str             # For tracking

    # From Classifier
    original_request: str
    classified_intent: str
    classifier_confidence: float

    # From Policy Agent
    policy_decision: str        # APPROVE, DENY, NEEDS_CLARIFICATION, ESCALATE
    cited_policies: List[str]   # Policy names applied
    handbook_citations: List[str]  # Quoted text from handbook

    # Response hints from Policy Agent
    should_apologize: bool
    should_mention_timeline: bool
    is_escalating: bool

    # If NEEDS_CLARIFICATION (from Policy Agent)
    clarification_questions: Optional[List[str]]

    # Tone/context
    is_upset_customer: bool     # From classifier escalation_reason
```

Example:

```json
{
	"request_id": "req_20260415_001",
	"original_request": "I was charged twice and this is ridiculous!",
	"classified_intent": "refund_request",
	"classifier_confidence": 0.92,
	"policy_decision": "APPROVE",
	"cited_policies": ["double_charge_refund"],
	"should_apologize": true,
	"should_mention_timeline": true,
	"is_upset_customer": true,
	"is_escalating": false
}
```

## Output Schema

```python
@dataclass
class ResponseAgentOutput:
    request_id: str             # Echo input request_id

    # Main response
    response_text: str          # Customer-facing message
    response_type: str          # "answer", "clarification_request", "escalation_notice"

    # Metadata
    tone: str                   # "professional", "empathetic", "firm"
    handbook_citations: List[str]  # Policies quoted
    cited_policies: List[str]

    # Action (if any)
    recommended_action: Optional[str]  # "issue_refund", "cancel_account", "create_escalation_ticket"
    action_parameters: Dict[str, Any]  # {"amount": 50.00, ...}

    # If escalating
    escalation_ticket_id: Optional[str]
    escalation_priority: Optional[str]  # "high", "normal"
```

Example:

```json
{
	"request_id": "req_20260415_001",
	"response_text": "I sincerely apologize for the billing error. I can see you were incorrectly charged twice on April 8th for $50 each. I've processed a refund of $50 back to your original payment method. You should see it within 5-7 business days. Thank you for bringing this to our attention.",
	"response_type": "answer",
	"tone": "empathetic",
	"recommended_action": "issue_refund",
	"action_parameters": {
		"amount": 50.0,
		"reason": "billing_error_double_charge"
	},
	"cited_policies": ["double_charge_refund"]
}
```

## Contract Guarantees

✅ **Response is always provided** (never null or empty)  
✅ **Tone matches situation** (empathetic for refunds, firm for policy denials, helpful for questions)  
✅ **Zero invented policies** (only cited_policies from handbook)  
✅ **No internal jargon** (customer-friendly language)  
✅ **Single unified response** (not multiple internal handoffs exposed)  
✅ **Feels personalized** (addresses customer's specific situation)  
✅ **Grounded in handbook** (every policy mention is quoted)

## Response Types

### Type 1: Answer (policy_decision = APPROVE)

**Template**:

```
[Optional apology if billing error]
[Acknowledgment of their specific situation]
[Answer/resolution]
[Timeline if refund]
[Thank you]
```

**Example**:

```
I sincerely apologize for the billing error. I can see you were incorrectly charged twice on April 8th for $50 each. I've processed a refund of $50 back to your original payment method. You should see it within 5-7 business days depending on your card issuer. Thank you for bringing this to our attention.
```

### Type 2: Denial (policy_decision = DENY)

**Template**:

```
[Thank them for reaching out]
[Explain the policy clearly]
[Reason their request doesn't qualify]
[What we could do instead, if anything]
[Offer escalation if they want to discuss]
```

**Example**:

```
Thank you for your request. We do consider refunds on a case-by-case basis, and here's where we are: requests for refunds covering multiple months due to "forgetting to cancel" aren't typically refunded retroactively. However, I'd be happy to refund your most recent month as a goodwill gesture. Would that work for you? If you'd like to discuss this further, I can escalate your request to my manager.
```

### Type 3: Clarification Request (policy_decision = NEEDS_CLARIFICATION)

**Template**:

```
[Acknowledge their request]
[Explain what info is needed and why]
[List questions clearly]
[Reassurance that we'll resolve once we have info]
```

**Example**:

```
Thank you for reaching out about your refund request. I'd like to help, but I need to clarify a couple of details first so I can look into this properly:

1. Which billing period are you referring to? (e.g., March, April)
2. What date were you charged?

Once I have this information, I can review your account and get you a quick answer.
```

### Type 4: Escalation (policy_decision = ESCALATE)

**Template**:

```
[Acknowledgment of situation]
[We need to escalate]
[What happens next]
[Timeframe for response]
```

**Example**:

```
Thank you for reaching out. I can see you've been having trouble with this issue over the past few weeks. I'm escalating your request to our support team lead who can give this the attention it deserves. You can expect to hear from them within 24 business hours.
```

## Error Handling

- If response_text generation fails → Use fallback: "Thank you for reaching out. We're looking into your request and will follow up shortly."
- If handbook citation cannot be found → Still provide answer, note that exact policy wasn't available
- If tone detection fails → Default to "professional"

## Implementation Location

`app/agents/response_generator.py::ResponseAgent`

---

## Quality Checklist

For each response, validate:

- [ ] No handbook rules invented
- [ ] No promises made outside policy (e.g., "definitely no fee" vs. "typically $X")
- [ ] Tone is appropriate to situation
- [ ] If refund, timeline mentioned (5-7 business days)
- [ ] If denial, reason is clear and grounded in policy
- [ ] If escalation, next steps are explained
- [ ] No multi-sentence jargon
- [ ] Personalized to customer's specific message (not generic template)
- [ ] If using handbook quotes, they're exact (not paraphrased)
- [ ] Doesn't repeat customer's escalatory language back
