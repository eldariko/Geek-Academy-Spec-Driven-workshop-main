"""Common response envelope models for MCP tool handlers."""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ToolError:
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(slots=True)
class ToolSuccess:
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"ok": True}
        result.update(self.payload)
        return result


@dataclass(slots=True)
class ActionResult:
    ok: bool
    payload: dict[str, Any] | None = None
    error: ToolError | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.ok:
            result: dict[str, Any] = {"ok": True}
            if self.payload:
                result.update(self.payload)
            return result
        return {"ok": False, "error": self.error.to_dict() if self.error else {"code": "INTERNAL_ERROR", "message": "Unknown error"}}
