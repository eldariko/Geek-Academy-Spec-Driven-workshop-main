# Geek-Academy-Spec-Driven-workshop-main Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-17

## Active Technologies
- Python 3.11+ + stdlib only (`dataclasses`, `datetime`, `json`, `pathlib`, `uuid`, `typing`) — no new packages (main)
- In-memory `list[AuditLogEntry]`; optional JSONL file appended via `--audit-log` CLI flag (main)

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
- main: Added Python 3.11+ + stdlib only (`dataclasses`, `datetime`, `json`, `pathlib`, `uuid`, `typing`) — no new packages

- 001-customer-support-agent: Added Python 3.11+

<!-- MANUAL ADDITIONS START -->
## Response Language Preference

- Always respond in English, even when the user writes in Hebrew.
<!-- MANUAL ADDITIONS END -->
