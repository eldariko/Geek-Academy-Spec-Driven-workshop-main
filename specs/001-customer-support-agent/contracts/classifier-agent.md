# Classifier Agent Contract

**Purpose**: Receives a customer request and determines intent  
**Pattern**: Pure function (deterministic, no side effects)  
**Framework**: Microsoft Agent Framework (MAF)

## Input Schema

```python
@dataclass
class ClassifierInput:
    request_id: str              # Unique request identifier
    raw_message: str             # Customer message text
    detected_keywords: List[str] # Optional: from preprocessing
    tone_indicators: Dict[str, float]  # Optional: sentiment analysis {"angry": 0.8}
```

Example:

```json
{
	"request_id": "req_20260415_001",
	"raw_message": "I want to cancel my subscription.",
	"detected_keywords": ["cancel", "subscription"],
	"tone_indicators": {}
}
```

## Output Schema

```python
@dataclass
class ClassifierOutput:
    request_id: str             # Echo of input request_id
    classified_intent: str      # One of: simple_question, refund_request, cancellation_request, escalation_needed
    confidence_score: float     # 0.0-1.0
    reasoning: str              # Explanation of classification (for audit)
    escalation_reason: Optional[str]  # If escalation_needed, why
```

Example:

```json
{
	"request_id": "req_20260415_001",
	"classified_intent": "cancellation_request",
	"confidence_score": 0.98,
	"reasoning": "Message explicitly contains 'cancel' with clear intent",
	"escalation_reason": null
}
```

## Contract Guarantees

✅ **Always returns one of four intents** (never null, never unknown)  
✅ **Confidence score is 0.0-1.0** (never out of range)  
✅ **Reasoning is always provided** (for audit trail)  
✅ **If escalation_needed, escalation_reason is non-null**  
✅ **Deterministic** (same input always produces same output)  
✅ **Does NOT** call policy engine or handbook (single responsibility)

## Error Handling

- If raw_message is empty → Output: escalation_needed, reasoning: "No content to classify"
- If classification is ambiguous (confidence < 0.7) → Try LLM fallback, else escalation_needed
- If LLM call fails → Fallback to rule-based; if all fails → escalation_needed

## Implementation Location

`app/agents/classifier.py::ClassifierAgent`

---

## Test Cases

| Input                          | Expected Intent      | Confidence | Notes                         |
| ------------------------------ | -------------------- | ---------- | ----------------------------- |
| "I want to cancel"             | cancellation_request | 0.95+      | Explicit keyword              |
| "Can I get a refund?"          | refund_request       | 0.90+      | Explicit word + question mark |
| "I was charged twice"          | refund_request       | 0.90+      | Implicit refund context       |
| "How do I change my password?" | simple_question      | 0.95+      | Product usage question        |
| "You people are thieves!"      | escalation_needed    | 0.90+      | Abusive language              |
| "Um, I'm mad about something"  | escalation_needed    | 0.70+      | High upset, vague issue       |
| Empty string                   | escalation_needed    | 0.95+      | No content                    |
