# Quickstart: Customer Support Agent

**Purpose**: Get the support agent application running with MAF workflows  
**Audience**: Developers implementing Lab 1  
**Time to completion**: ~15 minutes (setup) + implementation time

---

## Prerequisites

Before starting, ensure you have:

1. **Python 3.11+** installed

   ```powershell
   python --version  # Should show Python 3.11.x or higher
   ```

2. **Microsoft Agent Framework (MAF)** - Latest version
   - Install via pip during setup below

3. **Foundry API Key** - From your Microsoft Foundry account
   - Set environment variable: `FOUNDRY_API_KEY=your_key_here`

4. **Git** - This project uses Spec Kit hooks

   ```powershell
   git --version
   ```

5. **VS Code** (recommended) with Python extension

---

## Environment Setup

### Windows (PowerShell)

```powershell
# 1. Navigate to project directory
cd support-agent-python

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Set Foundry API key
$env:FOUNDRY_API_KEY = "your_key_here"

# 5. Verify installation
python -c "import azure.agent; print('MAF installed successfully')"
```

### macOS / Linux (Bash)

```bash
# 1. Navigate to project directory
cd support-agent-python

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Set Foundry API key
export FOUNDRY_API_KEY="your_key_here"

# 5. Verify installation
python -c "import azure.agent; print('MAF installed successfully')"
```

---

## Project Structure Quick Reference

```
support-agent-python/
├── main.py                 # CLI entry point — start here
├── app/
│   ├── orchestrator.py     # Workflow coordinator
│   ├── agents/            # Classifier, PolicyAgent, ResponseAgent
│   ├── models/            # Request/Response data classes
│   ├── services/          # Handbook, policy engine, classifier logic
│   ├── workflows/         # MAF workflow definitions
│   └── console_ui.py      # Console rendering
├── data/
│   ├── support_handbook.md    # Company policy (read-only)
│   └── sample_requests.md     # Test cases
└── tests/                # Unit + integration tests
```

**Important**: Don't edit `support_handbook.md` — it's the source of truth for all policies. All responses must be grounded in this file.

---

## First Run: Hello World Agent

Test that MAF is working:

```python
# test_setup.py
from azure.agent import Agent, ToolSet

# Create a simple test agent
async def main():
    # MAF agent initialization
    agent = Agent(name="TestAgent")
    print("✓ MAF Agent initialized successfully")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

Run it:

```powershell
python test_setup.py
```

Expected output:

```
✓ MAF Agent initialized successfully
```

---

## Workflow Architecture Overview

The support agent uses three chained MAF agents:

```
[Classifier Agent] → [Policy Agent] → [Response Agent]
       ↓                  ↓                  ↓
  Intent type      Policy decision    Customer response
```

### Step 1: Classifier Agent

- **Input**: Customer message (raw text)
- **Output**: Intent classification (refund, cancel, question, escalate)
- **Location**: `app/agents/classifier.py`
- **Key method**: `async def classify(request: CustomerRequest) → Classification`

### Step 2: Policy Agent

- **Input**: Classified intent + customer context
- **Output**: Policy decision (approve, deny, clarify, escalate)
- **Location**: `app/services/policy_engine.py`
- **Key method**: `async def evaluate(classification, context) → PolicyDecision`

### Step 3: Response Agent

- **Input**: Policy decision + original request
- **Output**: Unified customer-facing response
- **Location**: `app/agents/response_generator.py`
- **Key method**: `async def generate(policy_decision) → SupportResponse`

---

## Running the Application

### Interactive Console Mode

```powershell
python main.py
```

This starts an interactive console:

```
=== Customer Support Agent ===
Enter customer request (or 'quit' to exit):
> I was charged twice last week and I want my money back!

Analyzing request...
[Classifier] Intent: refund_request (confidence: 0.92)
[Policy] Decision: APPROVE (billing_error)
[Response] Generating response...

=== RESPONSE ===
I sincerely apologize for the billing error. I can see you were incorrectly charged twice last week. I've processed a refund back to your original payment method. You should see it within 5-7 business days.

[Action: issue_refund]
```

### Test with Sample Requests

```powershell
python main.py --test-mode
```

This processes all sample requests from `data/sample_requests.md` and shows:

- Classification accuracy
- Policy decision consistency
- Response quality

### Batch Processing

```powershell
python main.py --batch requests.json
```

Input file format (`requests.json`):

```json
[
	{
		"request_id": "test_001",
		"message": "How do I cancel my account?",
		"customer_id": "cust_123"
	},
	{
		"request_id": "test_002",
		"message": "I want a refund",
		"customer_id": "cust_456"
	}
]
```

---

## Data Models You'll Implement

These are the core data structures. See [data-model.md](data-model.md) for detailed schemas:

```python
# In app/models/

@dataclass
class CustomerRequest:
    raw_message: str
    request_id: str
    # ...

@dataclass
class ClassificationResult:
    classified_intent: str  # "simple_question" | "refund_request" | ...
    confidence_score: float
    # ...

@dataclass
class PolicyEvaluation:
    final_decision: str     # "APPROVE" | "DENY" | "NEEDS_CLARIFICATION" | "ESCALATE"
    evaluated_rules: List[PolicyMatch]
    # ...

@dataclass
class SupportResponse:
    response_text: str
    response_type: str      # "answer" | "clarification_request" | "escalation_notice"
    recommended_action: Optional[str]  # "issue_refund", "cancel_account"
    # ...
```

---

## Key Services Layer

### HandbookService

Loads and searches the support handbook:

```python
# Usage
handbook = HandbookService("data/support_handbook.md")

# Retrieve policy section
refund_policy = handbook.get_section("Refunds")

# Search for relevant info
search_results = handbook.search("double charge", context="billing")
```

**Location**: `app/services/handbook_service.py`

### PolicyEngine

Evaluates policies against requests:

```python
# Usage
engine = PolicyEngine(handbook)

# Evaluate a request against all policies
decision = engine.evaluate(
    intent="refund_request",
    customer_context={"account_created_date": ...},
    extracted_details={"charge_amount": 50.00, "charge_date": ...}
)

print(decision.final_decision)  # "APPROVE"
print(decision.evaluated_rules)  # All rules checked
```

**Location**: `app/services/policy_engine.py`

### Classifier

Determines customer intent:

```python
# Hybrid approach: fast rules + LLM fallback
classifier = Classifier(
    fast_rules=True,     # Use regex/keyword rules first
    llm_fallback=True    # Use Foundry for ambiguous cases
)

# Classify a message
result = await classifier.classify(
    message="I want to cancel my subscription",
    tone_indicators={"urgent": 0.3}
)

print(result.classified_intent)  # "cancellation_request"
```

**Location**: `app/services/intent_classifier.py` + `app/agents/classifier.py`

---

## Testing Your Implementation

### Unit Tests

```powershell
# Run all tests
pytest

# Run specific test file
pytest tests/test_classifier.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### Testing Classifier

```python
# tests/test_classifier.py
import pytest
from app.agents.classifier import ClassifierAgent

@pytest.mark.asyncio
async def test_classify_refund_request():
    classifier = ClassifierAgent()
    result = await classifier.classify(
        message="I was charged twice"
    )
    assert result.classified_intent == "refund_request"
    assert result.confidence_score >= 0.85
```

### Testing Policy Engine

```python
# tests/test_policy_engine.py
from app.services.policy_engine import PolicyEngine
from app.models import ClassificationResult

def test_approve_double_charge():
    engine = PolicyEngine(handbook)
    result = engine.evaluate(
        intent="refund_request",
        charge_count=2,
        charge_same_date=True
    )
    assert result.final_decision == "APPROVE"
```

### Testing Response Generation

```python
# tests/test_response_generator.py
from app.agents.response_generator import ResponseAgent

@pytest.mark.asyncio
async def test_response_mentions_handbook():
    responder = ResponseAgent()
    response = await responder.generate(
        policy_decision="APPROVE",
        should_apologize=True
    )
    assert "apologize" in response.response_text.lower()
    assert len(response.handbook_citations) > 0
```

---

## Debug Mode

Enable verbose logging:

```powershell
python main.py --debug
```

This outputs:

- Full agent execution traces
- Policy rule matches/mismatches
- LLM prompts and responses
- Workflow state at each step

Example debug output:

```
[DEBUG] Classifier input: "I want my money back for the double charge"
[DEBUG] Fast classifier: keywords ['money', 'charge'] found
[DEBUG] Confidence: 0.88, trying fast rules...
[DEBUG] Rule 'billing_error' matched!
[DEBUG] ClassificationResult: refund_request (0.88)

[DEBUG] Policy input: refund_request, customer_id=cust_456
[DEBUG] Evaluating rules...
[DEBUG]   - first_month_refund: no match (account 8 months old)
[DEBUG]   - billing_error_refund: MATCH ✓
[DEBUG] PolicyDecision: APPROVE
```

---

## Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'azure.agent'`

**Solution**: MAF not installed. Run:

```powershell
pip install azure-agent-framework
```

### Issue: `FOUNDRY_API_KEY not found`

**Solution**: Environment variable not set. On Windows:

```powershell
$env:FOUNDRY_API_KEY = "your_key"

# Or add to your profile for persistence:
Add-Content $PROFILE "`n`$env:FOUNDRY_API_KEY = 'your_key'"
```

### Issue: Classifier always returns `simple_question`

**Solution**: Check that fast rules are working. Debug with:

```powershell
python -c "
from app.services.intent_classifier import FastClassifier
classifier = FastClassifier()
result = classifier.classify('I want a refund')
print(result)
"
```

### Issue: Handbook not loading

**Solution**: Verify file exists:

```powershell
Test-Path support-agent-python/data/support_handbook.md

# If not found, copy from lab template:
Copy-Item ../lab_templates/support_handbook.md data/
```

---

## Next Steps

1. **Implement Classifier Agent** → `app/agents/classifier.py`
   - Start with `FastClassifier` (regex rules)
   - Add LLM fallback for confidence < 0.8

2. **Implement Policy Engine** → `app/services/policy_engine.py`
   - Define PolicyRule base class
   - Implement 5 refund rules (see spec.md)
   - Implement cancellation + escalation rules

3. **Implement Response Generator** → `app/agents/response_generator.py`
   - Map policy decision to response template
   - Ensure handbook citations included
   - Test tone + personalization

4. **Wire Workflow** → `app/workflows/main_workflow.py`
   - Orchestrate the three agents
   - Add error handling + escalation
   - Add audit logging

5. **Test End-to-End**
   - Run with sample requests
   - Validate against spec.md requirements
   - Check handbook compliance

---

## Resources

- [Microsoft Agent Framework Docs](https://learn.microsoft.com/en-us/agent-framework/)
- [Feature Spec](spec.md) — Requirements & user stories
- [Data Model](data-model.md) — Entity definitions
- [Agent Contracts](contracts/) — Interface specifications
- [Research Document](research.md) — Technology decisions

---

## Getting Help

- **Environment issues**: Check `FOUNDRY_API_KEY`, Python version, venv activation
- **MAF API questions**: See [Agent Framework documentation](https://learn.microsoft.com/en-us/agent-framework/)
- **Policy logic**: Review `data/support_handbook.md` + `contracts/policy-agent.md`
- **Design clarity**: Check data-model.md or research.md for context

Good luck! 🚀
