# Workflow Orchestration Contract

**Purpose**: Defines the MAF workflow orchestration logic and handoff between agents  
**Pattern**: Directed acyclic graph (DAG) of agent calls  
**Framework**: Microsoft Agent Framework (MAF)

## Workflow Definition

### Main Workflow: SupportRequestWorkflow

```
Input: CustomerRequest
  ↓
[Classifier Agent]
  ├─ Output: ClassificationResult
  ├─ If escalation_needed → Jump to Escalation Handler
  └─ Else continue
  ↓
[Policy Agent]
  ├─ Input: ClassificationResult + CustomerRequest
  ├─ Output: PolicyEvaluation
  ├─ If NEEDS_CLARIFICATION → Ask customer for more info (pause workflow)
  │                             Return ClarificationRequest
  ├─ If ESCALATE → Jump to Escalation Handler
  └─ Else continue
  ↓
[Response Agent]
  ├─ Input: ClassificationResult + PolicyEvaluation + CustomerRequest
  ├─ Output: SupportResponse
  └─ Return to user
  ↓
Output: SupportResponse
```

### Alternative Flow: Escalation Handler

```
Triggered when:
  - ClassificationResult.escalation_needed = true
  - PolicyDecision.final_decision = ESCALATE
  - Any agent encounters error

[Escalation Handler]
  ├─ Creates escalation ticket
  ├─ Logs context
  ├─ Returns: EscalationNotice (customer-facing message)
  └─ Forwards full context to human queue
```

## MAF Workflow Schema

```python
@dataclass
class SupportRequestWorkflow:
    """MAF Workflow definition for customer support requests"""

    # Workflow metadata
    workflow_id: str = "support_request_v1"

    # Agent definitions (will be registered with MAF)
    agents: Dict[str, AgentDefinition] = {
        "classifier": ClassifierAgent(),
        "policy": PolicyAgent(),
        "response_generator": ResponseAgent(),
    }

    # Workflow execution logic
    def execute(self, request: CustomerRequest) -> SupportResponse | EscalationNotice:
        """Execute support workflow"""

        # Step 1: Classify
        classification = self.agents["classifier"].run(request)

        if classification.escalation_needed:
            return self._handle_escalation(request, classification)

        # Step 2: Evaluate Policy
        policy_eval = self.agents["policy"].run({
            "request": request,
            "classification": classification,
        })

        if policy_eval.final_decision == "NEEDS_CLARIFICATION":
            return ClarificationRequest(
                request_id=request.request_id,
                missing_fields=policy_eval.clarification_needed_fields,
                questions=policy_eval.clarification_questions,
            )

        if policy_eval.final_decision == "ESCALATE":
            return self._handle_escalation(request, classification, policy_eval)

        # Step 3: Generate Response
        response = self.agents["response_generator"].run({
            "request": request,
            "classification": classification,
            "policy_eval": policy_eval,
        })

        return response

    def _handle_escalation(self, request, classification, policy_eval=None):
        """Create escalation ticket and return notice to customer"""
        ticket = self._create_escalation_ticket(request, classification, policy_eval)
        return EscalationNotice(
            request_id=request.request_id,
            ticket_id=ticket.id,
            priority=ticket.priority,
            next_steps="Your request has been escalated. You will hear from our team lead within 24 hours."
        )
```

## Message Flow Diagrams

### Happy Path (Simple Question)

```
User: "How do I change my password?"
  ↓
[Classifier] → "simple_question" (confidence: 0.98)
  ↓
[PolicyAgent] → Decision: APPROVE (answer from handbook)
  ↓
[ResponseAgent] → "To change your password, go to Settings > Security > Change Password"
  ↓
Output: Customer receives answer
```

### Conditional Path (Clarification Needed)

```
User: "I want a refund"
  ↓
[Classifier] → "refund_request" (confidence: 0.9)
  ↓
[PolicyAgent] → Decision: NEEDS_CLARIFICATION
               Missing: billing_date, charge_amount
  ↓
Output: ClarificationRequest
        "When were you charged and for how much?"
  ↓
User responds with details
  ↓
[Resume at PolicyAgent with new info]
  ↓
[PolicyAgent] → Decision: APPROVE
  ↓
[ResponseAgent] → Refund confirmation
  ↓
Output: Customer refund is processed
```

### Escalation Path

```
User: "You people are THIEVES! Lawyer INCOMING"
  ↓
[Classifier] → "escalation_needed" (legal_mention)
  ↓
[Escalation Handler] → Creates high-priority ticket
  ↓
Output: EscalationNotice
        "Your request has been escalated to our team lead. You will hear from them within 24 hours."
  ↓
Human support agent takes over
```

## WorkflowState Evolution

As request flows through agents, WorkflowState accumulates:

```python
# Initial state
state = WorkflowState(
    request=customer_request,
    request_id="req_001"
)

# After Classifier
state.classification = ClassificationResult(...)
state.agent_log.append("[14:23:45] Classifier: classified as refund_request")

# After Policy Agent
state.policy_evaluation = PolicyEvaluation(...)
state.agent_log.append("[14:23:47] PolicyAgent: APPROVE for billing_error_refund")

# After Response Agent
state.response = SupportResponse(...)
state.agent_log.append("[14:23:48] ResponseAgent: composed customer response")

# Final state ready for output
assert state.response is not None
print(f"Workflow completed in {0.003} seconds")
print(f"Request {state.request_id} → {state.response.response_type}")
```

## Workflow Constraints & Guarantees

✅ **Atomic request processing** — Each request gets exactly one workflow execution  
✅ **Sequential agent execution** — Agents run in order, no race conditions  
✅ **State isolation** — Each workflow run has independent state  
✅ **Early exit points** — Escalation detected early and short-circuits workflow  
✅ **Audit trail** — Every agent step logged for compliance  
✅ **Error recovery** — Any agent error triggers escalation (fail-safe to human)  
✅ **Timeout protection** — Workflow has max 10 second timeout (Foundry limit)

## Error Handling in Workflow

| Error                     | Where          | Action                       |
| ------------------------- | -------------- | ---------------------------- |
| Classifier timeout        | Classifier     | Escalate                     |
| Handbook unavailable      | PolicyAgent    | Escalate                     |
| LLM API unreachable       | PolicyAgent    | Escalate + retry             |
| Unknown intent            | Classification | Escalate                     |
| Response generation fails | ResponseAgent  | Fallback response + escalate |
| WorkflowState corruption  | Any            | Log + escalate               |

## Implementation Location

`app/workflows/main_workflow.py::SupportRequestWorkflow`

---

## Testing Strategy

### Unit Tests (per agent)

- Classifier: Intent detection accuracy
- PolicyAgent: Rule evaluation correctness
- ResponseAgent: Response quality + formatting

### Integration Tests (workflow)

- Happy path end-to-end
- Escalation triggers correctly
- Clarification pause/resume works
- State accumulation is correct

### Contract Tests (between agents)

- ClassifierOutput matches PolicyAgentInput schema
- PolicyEvaluation matches ResponseAgentInput schema
- All response types produce valid SupportResponse

### Smoke Tests (end-to-end)

- Sample requests from handbook produce correct intents
- All handbook policies are applied correctly
- No invented rules appear in responses
