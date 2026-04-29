"""Human Approval Service — collects operator decisions for refund requests"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from app.models.approval import AuditLogEntry, HumanDecision, Recommendation
from app.console_ui import render_approval_prompt


class HumanApprovalService:
    """Presents refund recommendations to an operator and records their decisions."""

    def __init__(
        self,
        audit_log_path: Optional[str] = None,
        input_fn: Callable[[str], str] = input,
        operator_id: str = "console",
    ):
        self._audit_log_path = audit_log_path
        self._input_fn = input_fn
        self._operator_id = operator_id
        self._audit_log: list[AuditLogEntry] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def request_approval(self, recommendation: Recommendation, request_text: str = "") -> HumanDecision:
        """Present recommendation to operator, collect decision, write audit entry.

        Blocks until the operator provides a valid 'approve' or 'reject' input.
        Retries indefinitely on unrecognized input.

        Args:
            recommendation: Populated Recommendation dataclass.
            request_text: Optional original customer message for display in the prompt.

        Returns:
            HumanDecision with all fields populated.

        Raises:
            IOError: If audit_log_path is set but cannot be written.
        """
        render_approval_prompt(recommendation, request_text)

        # Collect decision — retry until valid
        while True:
            raw_decision = self._input_fn("Enter decision [approve/reject]: ").strip().lower()
            if raw_decision in ("approve", "reject"):
                break

        # Collect optional note — preserve as-is, treat empty string as no note
        raw_note = self._input_fn("(Optional) Override note (press Enter to skip): ")
        operator_note: Optional[str] = raw_note if raw_note else None

        decided_at = datetime.now()
        overrides = raw_decision != recommendation.suggested_decision

        human_decision = HumanDecision(
            request_id=recommendation.request_id,
            decision=raw_decision,  # type: ignore[arg-type]
            operator_note=operator_note,
            operator_id=self._operator_id,
            decided_at=decided_at,
            overrides_recommendation=overrides,
        )

        # Write audit entry
        entry = AuditLogEntry(
            entry_id=uuid.uuid4().hex,
            request_id=recommendation.request_id,
            agent_recommendation=recommendation.suggested_decision,
            agent_reasoning=recommendation.reasoning,
            human_decision=raw_decision,  # type: ignore[arg-type]
            operator_note=operator_note,
            operator_id=self._operator_id,
            is_override=overrides,
            decided_at=decided_at,
        )
        self._audit_log.append(entry)

        if self._audit_log_path is not None:
            self._append_jsonl(entry)

        return human_decision

    def get_audit_log(self) -> list[AuditLogEntry]:
        """Return a shallow copy of the in-memory audit log."""
        return list(self._audit_log)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _append_jsonl(self, entry: AuditLogEntry) -> None:
        """Append an AuditLogEntry as a JSONL line to audit_log_path."""
        record = {
            "entry_id": entry.entry_id,
            "request_id": entry.request_id,
            "agent_recommendation": entry.agent_recommendation,
            "agent_reasoning": entry.agent_reasoning,
            "human_decision": entry.human_decision,
            "operator_note": entry.operator_note,
            "operator_id": entry.operator_id,
            "is_override": entry.is_override,
            "decided_at": entry.decided_at.isoformat(),
        }
        path = Path(self._audit_log_path)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
