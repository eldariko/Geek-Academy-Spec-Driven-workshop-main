# Implementation Plan: SupportOps MCP Server

**Branch**: `003-create-feature-branch` | **Date**: 2026-04-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-supportops-mcp-server/spec.md`

## Summary

Extend the Lab 1 Python host agent with a standalone Python SupportOps MCP server that exposes one data-access tool (`get_customer_context`) and two business-action tools (`create_ticket`, `record_refund_event`). The host remains the orchestrator: it classifies requests, pulls customer context from MCP, evaluates policy from the handbook, invokes MCP actions when needed, and then returns a personalized final response. The design uses local Streamable HTTP MCP transport for independent validation with MCP Inspector before host integration.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Python stdlib (`json`, `dataclasses`, `datetime`, `pathlib`, `typing`, `uuid`) + MCP Python SDK (server + Streamable HTTP transport), existing `pytest` for tests  
**Storage**: JSON mock data (`mock-data-lab2/mock_customers.json`), in-memory ticket/refund event stores, optional JSONL audit/action append logs  
**Testing**: `pytest` unit tests for tools and host orchestration, plus MCP Inspector manual validation for transport/tool behavior  
**Target Platform**: Local developer machine (Windows/macOS/Linux), console host app + local HTTP MCP server (`http://localhost:5058/mcp`)  
**Project Type**: Two local Python apps (host CLI agent + standalone MCP server)  
**Performance Goals**: Local tool calls return promptly for workshop demo (target <1s for data lookup and <2s for action tool responses under normal local conditions)  
**Constraints**: Keep implementation workshop-sized, preserve existing host UX, host owns policy logic, MCP owns ground-truth data/actions, stateless request/response tool design  
**Scale/Scope**: Single-session workshop demo with small mock dataset and sequential request processing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution at `.specify/memory/constitution.md` contains placeholder template text only and defines no enforceable principles or active gates.

Gate result before Phase 0: PASS (no enforceable rules present).

Re-check after Phase 1 design: PASS. The design remains small, uses existing project patterns, and introduces no extra architecture layers beyond what the specification requires.

## Project Structure

### Documentation (this feature)

```text
specs/003-supportops-mcp-server/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
Geek-Academy-Spec-Driven-workshop-main/
├── support-agent-python/
│   ├── app/
│   │   ├── agents/
│   │   ├── services/
│   │   ├── workflows/
│   │   └── models/
│   ├── data/
│   ├── tests/
│   └── main.py
├── support-ops-mcp-python/
│   ├── app/
│   │   ├── tools/         # new: MCP tool handlers
│   │   ├── models/        # new: tool request/response schemas
│   │   └── services/      # new: customer data and action services
│   ├── requirements.txt
│   └── main.py
└── mock-data-lab2/
    └── mock_customers.json
```

**Structure Decision**: Use the existing two-project Python layout and keep MCP logic isolated to `support-ops-mcp-python`, while integrating host orchestration changes inside `support-agent-python`.

## Complexity Tracking

No constitution violations requiring justification.
