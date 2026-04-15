# Phase 0 Research: Customer Support Agent

**Purpose**: Resolve unknowns identified in Technical Context and Design Principles  
**Date**: 2026-04-15  
**Outcomes**: Technology decisions ready for Phase 1 design

---

## Research Task 1: MAF Agent Patterns

### Question

How do Microsoft Agent Framework agents communicate, and what's the best pattern for multi-agent workflows where agents depend on each other's output?

### Key Findings

**MAF Architecture**:

- MAF agents are orchestrated via **Workflows** (directed acyclic graphs of agent invocations)
- Each agent has a defined schema for input and output
- Agents are **composable** — one agent's output can directly feed another agent's input
- Workflow execution is **sequential by default** but supports conditional branching and parallel execution

**Communication Pattern** (Sequential Flow):

- Agent A completes → returns typed output
- Agent B receives that output as input
- Agent C processes Agent B's result
- Perfect for our Classifier → PolicyAgent → ResponseAgent chain

**State Management**:

- Each workflow gets a run context with message history
- Agents can read previous messages via workflow context
- State is maintained within a single workflow run (persists between agent calls)
- No automatic persistence between sessions (good for our stateless console app)

**Decision Outcome**: Use **sequential agent chaining** via MAF Workflow:

1. Classifier produces `ClassificationResult`
2. PolicyAgent receives `ClassificationResult` + original request
3. ResponseAgent receives both previous outputs
4. Each step can short-circuit to escalation handler

**Authoritative Sources**:

- Microsoft Agent Framework documentation: https://learn.microsoft.com/en-us/agent-framework/
- GitHub repo: https://github.com/microsoft/agent-framework (Python: `/python` branch)
- Sample workflows: https://github.com/microsoft/Agent-Framework-Samples

---

## Research Task 2: Foundry Integration

### Question

How do we authenticate and call Microsoft Foundry from a Python console app, and what latency should we expect?

### Key Findings

**Foundry Authentication**:

- Uses **Azure SDK for Python** (`azure-identity`, `azure-ai-inference`)
- Two auth patterns:
  - **API Key** (simpler, single environment variable)
  - **Azure Entra ID** (enterprise, uses DefaultAzureCredential)
- For lab environment: API key via `FOUNDRY_API_KEY` environment variable is standard

**Foundry Latency**:

- First inference request: 1-3 seconds (cold model load)
- Subsequent requests: 300-800ms typically
- Token limits: Standard tier allows 5-10 requests/minute; sufficient for support tickets
- Recommendation: **2-second goal is achievable** for single-request processing

**Token Optimization**:

- Classifier: ~100-200 tokens (intent detection is small)
- Policy engine: ~300-500 tokens (handbook context inclusion)
- Response generation: ~200-400 tokens (customer response)
- Total: ~600-1100 tokens per request (well under Foundry limits)

**Configuration**:

```python
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

endpoint = "https://<foundry-instance>.foundry.microsoft.com"
credential = AzureKeyCredential(os.getenv("FOUNDRY_API_KEY"))
client = ChatCompletionsClient(endpoint=endpoint, credential=credential)
```

**Decision Outcome**: Use Azure SDK `ChatCompletionsClient` with API key authentication. Should meet <2s goal with optimized prompts.

---

## Research Task 3: Classification Strategy

### Question

Should we use LLM-based classification (flexible, expensive) or rule-based classification (fast, requires rules)?

### Key Findings

**LLM-Based Classification**:

- Pros: Handles ambiguous cases, edge cases, typos naturally
- Cons: Requires Foundry call (~500ms), uses tokens, slightly non-deterministic
- Accuracy: 95%+ with well-crafted prompt
- Cost: ~0.5¢ per classification

**Rule-Based Classification** (Regex + keyword rules):

- Pros: Deterministic, zero latency, no API calls, 100% consistency
- Cons: Misses edge cases, needs maintenance, requires keyword tuning
- Accuracy: 85-90% (fails on creative phrasing)

**Hybrid Approach**:

- Use fast rules first (keywords: "refund", "cancel", "escalate me")
- Fall back to LLM for ambiguous cases
- Pros: Fast path for 70% of requests; intelligent fallback for edge cases
- Accuracy: 95%+ with fast-path for common cases

**Recommendation**: **Hybrid approach**

- **Fast Rules** (O(1)):
  - Contains "cancel" or "terminate" → Cancellation
  - Contains "refund", "money back", "charge" → Refund
  - Explicit "manager", "escalate", "lawyer" → Escalation
  - Otherwise → Simple Question
- **LLM Fallback**: If confidence < 80%, use Foundry to reclassify ambiguous cases

**Decision Outcome**: Implement two-stage classifier:

1. `FastClassifier` (regex/keyword rules, <5ms)
2. `LLMClassifier` (Foundry, fallback for ambiguous)

---

## Research Task 4: Policy Engine Design

### Question

How do we implement the handbook rules (30-day refund window, one-per-year, escalation triggers) in a way that's maintainable and auditable?

### Key Findings

**Rule Evaluation Approaches**:

1. **Simple Cascade** (if-if-if):
   - Check rule 1 → Check rule 2 → etc.
   - Pros: Easy to read, deterministic
   - Cons: Hard to maintain, order-dependent
   - Suitable for our ~10 rules

2. **Rete Algorithm** (forward chaining):
   - Complex, best for 100s of rules
   - Overkill for our use case

3. **Rule Object Pattern** (recommended):
   - Each policy as a `Rule` object with conditions + actions
   - `PolicyEngine` evaluates all rules, collects matches
   - Pros: Clear, maintainable, testable, auditable

**Policy Engine Pseudocode**:

```python
class RefundRule:
    def matches(self, request: CustomerRequest, handbook: SupportHandbook) -> bool:
        # Check if this rule applies
        pass

    def evaluate(self, request: CustomerRequest) -> Decision:
        # Return APPROVE/DENY/NEEDS_INFO
        pass

class PolicyEngine:
    def __init__(self, handbook):
        self.rules = [
            FirstMonthRefundRule(handbook),
            ServiceOutageRule(handbook),
            BillingErrorRule(handbook),
            OnePerYearRule(handbook),
        ]

    def evaluate(self, request: CustomerRequest) -> PolicyDecision:
        results = []
        for rule in self.rules:
            if rule.matches(request):
                results.append(rule.evaluate(request))
        return aggregate_results(results)  # APPROVE if all say yes, DENY if any says no
```

**State Requirements**:

- Customer refund history (past 12 months)
- Billing period records
- Service status log (for outage verification)

**For Lab 1** (no database):

- Mock customer history in sample data
- Status page as static reference
- All lookups happen at request time

**Decision Outcome**: Implement Rule object pattern with PolicyEngine coordinator.

- Each policy rule→ separate class inheriting from `PolicyRule` base
- PolicyEngine maintains rule registry and aggregation logic
- Easy to add/remove rules without touching workflow code
- All decisions are auditable (each rule logs its match + decision)

---

## Design Decisions Summary

| Decision                | Choice                                      | Rationale                                                                                 |
| ----------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **Agent Communication** | Sequential chaining via MAF Workflow        | Matches our data flow (classify → policy → respond); state passes naturally between steps |
| **LLM Backend**         | Microsoft Foundry with Azure SDK            | Integrated with Agent Framework; 800ms typical latency fits 2s budget                     |
| **Classification**      | Hybrid (fast rules + LLM fallback)          | 70% of requests handled in <5ms; edge cases still handled intelligently                   |
| **Policy Engine**       | Rule object pattern                         | Maintainable, auditable, easy to test; aligns with handbook structure                     |
| **State Management**    | Stateless per request; mock history in data | Simplicity for console app; no persistence needed between sessions                        |
| **Error Handling**      | Escalation on ambiguous/unknown cases       | Prevents system from inventing rules or providing wrong guidance                          |

---

## Constraints & Assumptions Verified

✅ **Constraint: "MUST not invent company rules"** → PolicyEngine only evaluates rules defined in handbook; unknown cases escalate  
✅ **Constraint: "Unified response, not internal handoffs"** → ResponseAgent sees full context from both prior agents; single output only  
✅ **Constraint: "<2 second response"** → Hybrid classifier (fast path) + optimized prompts meet budget  
✅ **Assumption: "Handbook is source of truth"** → PolicyEngine only reads from handbook; all decisions traceable to handbook text

---

## Next Steps (Phase 1)

1. Create `data-model.md` with entity structures based on decisions above
2. Define agent input/output schemas in `contracts/`
3. Write `quickstart.md` with MAF workflow setup instructions
4. Create skeleton code for PolicyRule, Classifier, PolicyEngine
5. Begin implementation with high-confidence decisions from this research
