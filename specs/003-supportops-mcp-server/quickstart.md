# Quickstart: SupportOps MCP Server (Python)

**Feature**: 003-supportops-mcp-server  
**Date**: 2026-04-26

## Goal

Run and validate a standalone SupportOps MCP server, then integrate it with the Python host support agent.

## 1. Start the MCP server project

```bash
cd Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python
python -m venv .venv
```

Activate the environment:

- Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

- macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run server:

```bash
python main.py
```

Expected endpoint: `http://localhost:5058/mcp`

## 2. Validate with MCP Inspector

Start inspector in a second terminal:

```bash
npx -y @modelcontextprotocol/inspector
```

In Inspector:

1. Select transport: Streamable HTTP.
2. Connect to `http://localhost:5058/mcp`.
3. Confirm tools are listed:
   - `get_customer_context`
   - `create_ticket`
   - `record_refund_event`
4. Invoke at least:
   - One data access call (`get_customer_context`)
   - One action call (`create_ticket` or `record_refund_event`)

## 3. Integrate host app (Lab 1 Python)

```bash
cd ../support-agent-python
python -m venv .venv
python -m pip install -r requirements.txt
python main.py
```

Integration expectations:

1. Host classifies the request.
2. Host retrieves customer context through MCP.
3. Host evaluates policy from `data/support_handbook.md`.
4. Host triggers MCP action tool when policy requires it.
5. Host sends final personalized response.

## 4. End-to-end validation scenarios

1. Personalization scenario:
   - Known customer email returns `plan_type` and `name`.
   - Final response reflects customer plan context.
2. Escalation scenario:
   - Host policy outcome is escalation.
   - `create_ticket` is called and ticket id is returned.
3. Refund scenario:
   - Host policy approves refund.
   - `record_refund_event` is called.
   - Subsequent customer context includes new refund event.

## 5. Troubleshooting

- If endpoint connection fails, verify server is running and listening on port 5058.
- If tools are missing in Inspector, verify tool registration in MCP server startup.
- If host cannot call MCP, verify host MCP client endpoint and transport match Streamable HTTP.

## 6. Validation Log (2026-04-28)

### Scenario Matrix

1. Personalization scenario: PASS
   - Evidence: `test_customer_context_personalizes_response_for_known_customer`
   - Outcome: Host response includes customer name and plan-aware personalization.
2. Escalation action scenario: PASS
   - Evidence: `test_escalation_invokes_create_ticket_and_includes_ticket_id`
   - Outcome: Host invokes `create_ticket` and includes `ticket_id` in escalation response.
3. Refund recording scenario: PASS
   - Evidence: `test_refund_approval_records_event_and_mentions_reference`
   - Outcome: Host invokes `record_refund_event` and includes event reference in response.
4. Refund replay scenario: PASS
   - Evidence: `test_recorded_refund_event_is_visible_on_later_context_lookup`
   - Outcome: Subsequent customer context retrieval includes appended refund history.

### Automated Test Commands

1. MCP server unit contracts

```bash
cd Geek-Academy-Spec-Driven-workshop-main/support-ops-mcp-python
../support-agent-python/.venv/Scripts/python.exe -m pytest tests/unit -q
```

Result: `22 passed`

2. Host integration and regression tests

```bash
cd Geek-Academy-Spec-Driven-workshop-main/support-agent-python
.venv/Scripts/python.exe -m pytest tests/integration/test_customer_context_integration.py tests/integration/test_escalation_ticket_integration.py tests/integration/test_refund_event_integration.py tests/test_hitl_approval.py -q
```

Result: `33 passed`

### Manual Inspector Check

Manual MCP Inspector validation remains required for final sign-off.
