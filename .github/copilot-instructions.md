# Geek-Academy-Spec-Driven-workshop-main Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-26

## Active Technologies
- Python 3.11+ + stdlib only (`dataclasses`, `datetime`, `json`, `pathlib`, `uuid`, `typing`) — no new packages (main)
- In-memory `list[AuditLogEntry]`; optional JSONL file appended via `--audit-log` CLI flag (main)
- Python 3.11+ + Python stdlib (`json`, `dataclasses`, `datetime`, `pathlib`, `typing`, `uuid`) + MCP Python SDK (server + Streamable HTTP transport), existing `pytest` for tests (003-create-feature-branch)
- JSON mock data (`mock-data-lab2/mock_customers.json`), in-memory ticket/refund event stores, optional JSONL audit/action append logs (003-create-feature-branch)

- Python 3.11+ (001-customer-support-agent)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 003-create-feature-branch: Added Python 3.11+ + Python stdlib (`json`, `dataclasses`, `datetime`, `pathlib`, `typing`, `uuid`) + MCP Python SDK (server + Streamable HTTP transport), existing `pytest` for tests
- main: Added Python 3.11+ + stdlib only (`dataclasses`, `datetime`, `json`, `pathlib`, `uuid`, `typing`) — no new packages

- 001-customer-support-agent: Added Python 3.11+

<!-- MANUAL ADDITIONS START -->
## Response Language Preference

- Respond only in English. Do not reply in any other language unless the user explicitly asks for translation output.
<!-- MANUAL ADDITIONS END -->
