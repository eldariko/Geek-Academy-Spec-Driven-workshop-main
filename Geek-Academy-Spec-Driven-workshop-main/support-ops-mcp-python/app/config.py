"""Configuration constants for the SupportOps MCP server."""

from pathlib import Path

SERVER_NAME = "support-ops-mcp"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5058
SERVER_PATH = "/mcp"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CUSTOMER_DATA_PATH = PROJECT_ROOT / "mock-data-lab2" / "mock_customers.json"
