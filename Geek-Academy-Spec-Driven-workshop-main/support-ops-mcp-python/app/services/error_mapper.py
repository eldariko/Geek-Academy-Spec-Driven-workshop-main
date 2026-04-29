"""Error-code to response mapping for MCP tool handlers."""

from app.models.results import ActionResult, ToolError


KNOWN_CODES = {
    "INVALID_ARGUMENT": "Invalid or missing input",
    "CUSTOMER_NOT_FOUND": "Customer record was not found",
    "INVALID_PRIORITY": "Priority must be one of low|medium|high|urgent",
    "INVALID_AMOUNT": "Refund amount must be greater than zero",
    "INTERNAL_ERROR": "Internal server error",
}


def make_error(code: str, message: str | None = None) -> ActionResult:
    resolved_code = code if code in KNOWN_CODES else "INTERNAL_ERROR"
    resolved_message = message or KNOWN_CODES[resolved_code]
    return ActionResult(ok=False, error=ToolError(code=resolved_code, message=resolved_message))
