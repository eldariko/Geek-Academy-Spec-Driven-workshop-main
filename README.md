# General README — Python Support Agent

## Product Overview
This project delivers a **Customer Support Agent** that receives free-text customer requests and returns structured, policy-based responses.

The system follows a clear workflow:
1. Intent classification
2. Policy evaluation
3. Response generation

It can run both in interactive mode and in test mode with sample requests.

## Technology Choice
I chose to build the solution in **Python** because of:
- Fast development speed
- Readable, modular code
- Straightforward integration with Azure OpenAI services

## How I Built It
The implementation follows a **Spec-Driven Development** approach:
- Break the problem into clear business workflow steps
- Define structured input/output and workflow-state models
- Separate responsibilities into dedicated layers:
  - `app/agents` — classification and response generation
  - `app/services` — policy logic, handbook access, and LLM integration
  - `app/workflows` — end-to-end orchestration
  - `app/models` — domain models for requests and responses
- Add `--use-llm` mode to improve classification in ambiguous cases
- Expose execution through `main.py` with support for test mode

## Implementation Location
The implementation is located in:

`Geek-Academy-Spec-Driven-workshop-main/support-agent-python`

## Quick Run
1. Create a virtual environment
2. Install dependencies from `requirements.txt`
3. Create `.env` from `.env.example`
4. Run:

```bash
python main.py
```
