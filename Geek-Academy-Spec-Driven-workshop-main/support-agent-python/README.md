# Support Agent Python

Prerequisite: Python 3.10 or newer.

1. Create and activate a virtual environment:

```sh
python -m venv .venv
```

On macOS/Linux:

```sh
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If `python` is not available on your Mac, use `python3` instead for setup and run commands.

2. Run `python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and fill in your Azure OpenAI values.
   On macOS/Linux: `cp .env.example .env`
   In PowerShell: `Copy-Item .env.example .env`
4. Run:

```sh
python main.py
```

On macOS systems where only `python3` is available, run `python3 main.py`.

## SupportOps MCP Integration

The host remains the orchestrator and calls MCP tools for customer data and actions.

Set endpoint via environment variable or CLI:

- Environment: `SUPPORT_OPS_MCP_ENDPOINT=http://localhost:5058/mcp`
- CLI: `python main.py --mcp-endpoint http://localhost:5058/mcp`

Optional timeout override:

- `python main.py --mcp-endpoint http://localhost:5058/mcp --mcp-timeout 5`

Host fallback behavior when MCP fails:

- Customer-safe responses are still generated.
- MCP failures are captured in workflow state logs (`mcp_errors`).
- Escalation and refund actions degrade gracefully if action tools fail.

## Human Approval for Refund Requests

All refund requests require human operator approval before a response is sent to the customer. When a refund request is processed, the agent:

1. Evaluates the refund policy and produces a recommendation (`approve` or `reject`).
2. Displays the recommendation to the operator on the console.
3. Waits for the operator to enter `approve` or `reject`.
4. Optionally records an override note.
5. Uses the operator's decision (not the agent's recommendation) to generate the customer-facing response.

### Audit Log (`--audit-log`)

Pass `--audit-log <path>` to append every operator decision to a JSONL file (one JSON object per line):

```sh
python main.py --audit-log audit.jsonl
```

Each line is a valid JSON object with the following fields:

| Field                  | Type    | Description                                          |
| ---------------------- | ------- | ---------------------------------------------------- |
| `entry_id`             | string  | UUID hex — unique per decision                       |
| `request_id`           | string  | Links to the customer request                        |
| `agent_recommendation` | string  | `"approve"` or `"reject"` — what the agent suggested |
| `agent_reasoning`      | string  | Policy rationale                                     |
| `human_decision`       | string  | `"approve"` or `"reject"` — what the operator chose  |
| `operator_note`        | string? | Free-text note, or `null` if skipped                 |
| `operator_id`          | string  | `"console"` for single-operator sessions             |
| `is_override`          | boolean | `true` when operator overrides agent recommendation  |
| `decided_at`           | string  | ISO 8601 timestamp of the decision                   |

Example entry:

```json
{
	"entry_id": "a1b2c3d4...",
	"request_id": "req_20260423_...",
	"agent_recommendation": "approve",
	"agent_reasoning": "Within 30-day refund window",
	"human_decision": "reject",
	"operator_note": "Customer was warned previously",
	"operator_id": "console",
	"is_override": true,
	"decided_at": "2026-04-23T14:30:00.123456"
}
```
