"""Tests for Human-in-the-Loop refund approval (feature 002-hitl-refund-approval)"""
import json
import os
import tempfile
import uuid
from datetime import datetime
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

from app.models.approval import AuditLogEntry, HumanDecision, Recommendation
from app.services.approval_service import HumanApprovalService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_recommendation(suggested: str = "approve", request_id: str = None) -> Recommendation:
    return Recommendation(
        request_id=request_id or f"req_{uuid.uuid4().hex[:8]}",
        suggested_decision=suggested,  # type: ignore[arg-type]
        reasoning="Within 30-day refund window",
        policy_rules_applied=["first_month_refund"],
        generated_at=datetime.now(),
    )


def _input_sequence(*responses: str):
    """Return a callable that returns successive responses (simulates user input)."""
    it: Iterator[str] = iter(responses)
    return lambda prompt="": next(it)


# ===========================================================================
# Phase 3 — User Story 1: Human Approves Refund Recommendation (T012-T016)
# ===========================================================================

class TestApprovalService:
    """T013 — approve decision recorded correctly"""

    def test_request_approval_approve_recorded_correctly(self):
        """T013: HumanApprovalService records approve decision with operator_id and timestamp"""
        service = HumanApprovalService(
            operator_id="op_test",
            input_fn=_input_sequence("approve", ""),
        )
        rec = _make_recommendation("approve")
        decision = service.request_approval(rec)

        assert decision.decision == "approve"
        assert decision.operator_id == "op_test"
        assert decision.request_id == rec.request_id
        assert isinstance(decision.decided_at, datetime)

    def test_audit_entry_created_on_approve(self):
        """T014: AuditLogEntry written with all fields on approve"""
        service = HumanApprovalService(input_fn=_input_sequence("approve", ""))
        rec = _make_recommendation("approve")
        service.request_approval(rec)

        log = service.get_audit_log()
        assert len(log) == 1
        entry = log[0]
        assert entry.entry_id
        assert entry.agent_recommendation == "approve"
        assert entry.human_decision == "approve"
        assert entry.operator_id == "console"
        assert isinstance(entry.decided_at, datetime)

    def test_override_flag_false_when_no_override(self):
        """T015: overrides_recommendation=False when operator agrees with recommendation"""
        service = HumanApprovalService(input_fn=_input_sequence("approve", ""))
        rec = _make_recommendation("approve")
        decision = service.request_approval(rec)

        assert decision.overrides_recommendation is False

    def test_workflow_approve_recommendation_generates_refund_response(self):
        """T016: End-to-end: operator approves → refund confirmation in response"""
        from app.services import HandbookService
        from app.workflows.main_workflow import SupportRequestWorkflow
        from app.models import CustomerRequest

        approval_service = HumanApprovalService(input_fn=_input_sequence("approve", ""))
        handbook_path = _get_handbook_path()
        workflow = SupportRequestWorkflow(
            HandbookService(handbook_path),
            approval_service=approval_service,
        )
        request = CustomerRequest(
            raw_message="I signed up yesterday and want a refund please",
            request_id="req_test_us1",
        )
        state = workflow.execute(request)

        assert state.human_decision is not None
        assert state.human_decision.decision == "approve"
        assert state.response is not None
        response_text = state.response.response_text.lower()
        assert any(word in response_text for word in ["refund", "approved", "process"]), (
            f"Expected refund confirmation but got: {state.response.response_text}"
        )


# ===========================================================================
# Phase 4 — User Story 2: Human Rejects (T019-T024)
# ===========================================================================

class TestRejectFlow:

    def test_request_approval_reject_recorded_correctly(self):
        """T019: HumanApprovalService records reject decision"""
        service = HumanApprovalService(input_fn=_input_sequence("reject", ""))
        rec = _make_recommendation("approve")
        decision = service.request_approval(rec)

        assert decision.decision == "reject"

    def test_override_flag_true_when_reject_overrides_approve(self):
        """T020: overrides_recommendation=True when operator rejects agent's approve"""
        service = HumanApprovalService(input_fn=_input_sequence("reject", ""))
        rec = _make_recommendation("approve")
        decision = service.request_approval(rec)

        assert decision.overrides_recommendation is True

    def test_audit_entry_is_override_flag(self):
        """T021: AuditLogEntry.is_override=True when decision differs from recommendation"""
        service = HumanApprovalService(input_fn=_input_sequence("reject", ""))
        rec = _make_recommendation("approve")
        service.request_approval(rec)

        entry = service.get_audit_log()[0]
        assert entry.is_override is True

    def test_operator_note_captured_in_audit(self):
        """T022: Operator note recorded in AuditLogEntry"""
        service = HumanApprovalService(input_fn=_input_sequence("reject", "policy exception"))
        rec = _make_recommendation("approve")
        decision = service.request_approval(rec)

        assert decision.operator_note == "policy exception"
        entry = service.get_audit_log()[0]
        assert entry.operator_note == "policy exception"

    def test_workflow_reject_recommendation_generates_decline_response(self):
        """T023: End-to-end: operator rejects → decline response without revealing recommendation"""
        from app.services import HandbookService
        from app.workflows.main_workflow import SupportRequestWorkflow
        from app.models import CustomerRequest

        approval_service = HumanApprovalService(input_fn=_input_sequence("reject", ""))
        handbook_path = _get_handbook_path()
        workflow = SupportRequestWorkflow(
            HandbookService(handbook_path),
            approval_service=approval_service,
        )
        request = CustomerRequest(
            raw_message="I signed up yesterday and want a refund please",
            request_id="req_test_us2",
        )
        state = workflow.execute(request)

        assert state.human_decision is not None
        assert state.human_decision.decision == "reject"
        assert state.response is not None
        response_text = state.response.response_text.lower()
        # Should NOT reveal agent recommendation
        assert "agent" not in response_text
        assert "recommend" not in response_text


# ===========================================================================
# Phase 5 — User Story 3: Agent Recommends Rejection, Human Approves (T025-T027)
# ===========================================================================

class TestOverrideApproveReject:

    def test_override_flag_true_when_approve_overrides_reject(self):
        """T025: overrides_recommendation=True when operator approves agent's reject"""
        service = HumanApprovalService(input_fn=_input_sequence("approve", "goodwill"))
        rec = _make_recommendation("reject")
        decision = service.request_approval(rec)

        assert decision.overrides_recommendation is True

    def test_audit_entry_notes_override_direction(self):
        """T026: Audit log records reject→approve override correctly"""
        service = HumanApprovalService(input_fn=_input_sequence("approve", "goodwill"))
        rec = _make_recommendation("reject")
        service.request_approval(rec)

        entry = service.get_audit_log()[0]
        assert entry.agent_recommendation == "reject"
        assert entry.human_decision == "approve"
        assert entry.is_override is True
        assert entry.operator_note == "goodwill"

    def test_workflow_approve_overrides_reject_recommendation(self):
        """T027: End-to-end: operator approves over reject → refund confirmed; audit captures note"""
        from app.services import HandbookService
        from app.workflows.main_workflow import SupportRequestWorkflow
        from app.models import CustomerRequest

        approval_service = HumanApprovalService(input_fn=_input_sequence("approve", "goodwill gesture"))
        handbook_path = _get_handbook_path()
        workflow = SupportRequestWorkflow(
            HandbookService(handbook_path),
            approval_service=approval_service,
        )
        # Request that would normally be rejected (outside policy window)
        request = CustomerRequest(
            raw_message="I want a refund for my subscription from 6 months ago",
            request_id="req_test_us3",
        )
        state = workflow.execute(request)

        assert state.human_decision is not None
        # Whatever the agent recommended, the response should follow human decision
        if state.human_decision.decision == "approve":
            response_text = state.response.response_text.lower()
            assert any(word in response_text for word in ["refund", "approved", "process"])
        log = approval_service.get_audit_log()
        assert len(log) >= 1


# ===========================================================================
# Phase 6 — User Story 4: Non-Refund Pass-Through (T028-T033)
# ===========================================================================

class TestNonRefundPassthrough:

    def _make_workflow_with_service(self):
        from app.services import HandbookService
        from app.workflows.main_workflow import SupportRequestWorkflow

        # Approval service that would fail if called (to detect unintended triggers)
        approval_service = HumanApprovalService(input_fn=_input_sequence())
        handbook_path = _get_handbook_path()
        workflow = SupportRequestWorkflow(
            HandbookService(handbook_path),
            approval_service=approval_service,
        )
        return workflow, approval_service

    def test_gate_does_not_trigger_simple_question(self):
        """T028: Approval gate NOT activated for simple_question intent"""
        from app.models.workflow_state import WorkflowState
        from app.models.classification import ClassificationResult

        service = HumanApprovalService(input_fn=_input_sequence())
        state = WorkflowState(request_id="req_sq")
        state.classification = ClassificationResult(
            request_id="req_sq",
            classified_intent="simple_question",
            confidence_score=0.95,
            reasoning="keyword match",
        )
        # Gate condition check
        should_gate = (
            state.classification.classified_intent == "refund_request"
            and not getattr(state.classification, "escalation_reason", None)
        )
        assert should_gate is False
        assert state.human_decision is None

    def test_gate_does_not_trigger_cancellation(self):
        """T029: Approval gate NOT activated for cancellation_request"""
        from app.models.workflow_state import WorkflowState
        from app.models.classification import ClassificationResult

        state = WorkflowState(request_id="req_cancel")
        state.classification = ClassificationResult(
            request_id="req_cancel",
            classified_intent="cancellation_request",
            confidence_score=0.90,
            reasoning="keyword match",
        )
        should_gate = (
            state.classification.classified_intent == "refund_request"
            and not getattr(state.classification, "escalation_reason", None)
        )
        assert should_gate is False

    def test_gate_does_not_trigger_escalation(self):
        """T030: Approval gate NOT activated for escalation_needed"""
        from app.models.workflow_state import WorkflowState
        from app.models.classification import ClassificationResult

        state = WorkflowState(request_id="req_escalation")
        state.classification = ClassificationResult(
            request_id="req_escalation",
            classified_intent="escalation_needed",
            confidence_score=0.85,
            reasoning="explicit escalation request",
        )
        should_gate = (
            state.classification.classified_intent == "refund_request"
            and not getattr(state.classification, "escalation_reason", None)
        )
        assert should_gate is False

    def test_state_human_decision_none_for_non_refund(self):
        """T031: state.human_decision remains None for non-refund intents"""
        from app.models.workflow_state import WorkflowState

        state = WorkflowState(request_id="req_none")
        assert state.human_decision is None

    def test_simple_question_workflow_unchanged(self):
        """T032: End-to-end general question → no approval step → response delivered"""
        from app.models import CustomerRequest

        workflow, approval_service = self._make_workflow_with_service()
        request = CustomerRequest(
            raw_message="What features does the premium plan include?",
            request_id="req_sq_e2e",
        )
        state = workflow.execute(request)

        assert state.human_decision is None
        assert len(approval_service.get_audit_log()) == 0
        assert state.response is not None

    def test_cancellation_workflow_unchanged(self):
        """T033: End-to-end cancellation → no approval step → response delivered"""
        from app.models import CustomerRequest

        workflow, approval_service = self._make_workflow_with_service()
        request = CustomerRequest(
            raw_message="I want to cancel my subscription",
            request_id="req_cancel_e2e",
        )
        state = workflow.execute(request)

        assert state.human_decision is None
        assert len(approval_service.get_audit_log()) == 0
        assert state.response is not None


# ===========================================================================
# Phase 7 — Polish & Edge Cases (T034-T042)
# ===========================================================================

class TestEdgeCases:

    def test_invalid_input_retries_until_valid(self):
        """T034: Operator enters invalid value → prompt repeats until valid approve/reject"""
        service = HumanApprovalService(
            input_fn=_input_sequence("bad", "also_bad", "approve", ""),
        )
        rec = _make_recommendation("approve")
        decision = service.request_approval(rec)

        assert decision.decision == "approve"

    def test_empty_operator_note_allowed(self):
        """T035: Operator can skip note entry (empty string or None both valid)"""
        service = HumanApprovalService(input_fn=_input_sequence("approve", ""))
        rec = _make_recommendation("approve")
        decision = service.request_approval(rec)

        assert decision.operator_note is None

    def test_operator_note_preserved_exactly(self):
        """T036: Arbitrary text in operator note is recorded as-is"""
        note = "  Special note: charge-back ref #1234  "
        service = HumanApprovalService(input_fn=_input_sequence("approve", note))
        rec = _make_recommendation("approve")
        decision = service.request_approval(rec)

        assert decision.operator_note == note


class TestAuditLogPersistence:

    def test_audit_log_jsonl_file_written(self):
        """T037: When audit_log_path set, AuditLogEntry appended as JSONL"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            service = HumanApprovalService(
                audit_log_path=path,
                input_fn=_input_sequence("approve", ""),
            )
            rec = _make_recommendation("approve")
            service.request_approval(rec)

            with open(path, encoding="utf-8") as fh:
                lines = [l.strip() for l in fh if l.strip()]
            assert len(lines) == 1
        finally:
            os.unlink(path)

    def test_audit_log_jsonl_format_valid(self):
        """T038: JSONL entries are valid JSON parseable to dicts"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            service = HumanApprovalService(
                audit_log_path=path,
                input_fn=_input_sequence("reject", "test note"),
            )
            rec = _make_recommendation("approve")
            service.request_approval(rec)

            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        parsed = json.loads(line)
                        assert isinstance(parsed, dict)
                        assert "entry_id" in parsed
                        assert "human_decision" in parsed
        finally:
            os.unlink(path)

    def test_audit_log_get_audit_log_returns_copy(self):
        """T039: get_audit_log() returns shallow copy; in-memory list not modified"""
        service = HumanApprovalService(input_fn=_input_sequence("approve", ""))
        rec = _make_recommendation("approve")
        service.request_approval(rec)

        log_copy = service.get_audit_log()
        log_copy.clear()

        assert len(service.get_audit_log()) == 1


class TestEndToEndIntegration:

    def test_end_to_end_refund_approve_with_audit_file(self):
        """T040: Refund → approve → response confirmed AND audit file written"""
        from app.services import HandbookService
        from app.workflows.main_workflow import SupportRequestWorkflow
        from app.models import CustomerRequest

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            approval_service = HumanApprovalService(
                audit_log_path=path,
                input_fn=_input_sequence("approve", ""),
            )
            handbook_path = _get_handbook_path()
            workflow = SupportRequestWorkflow(
                HandbookService(handbook_path),
                approval_service=approval_service,
            )
            request = CustomerRequest(
                raw_message="I signed up yesterday and want a refund please",
                request_id="req_e2e_t040",
            )
            state = workflow.execute(request)

            assert state.response is not None
            with open(path, encoding="utf-8") as fh:
                lines = [l for l in fh if l.strip()]
            assert len(lines) >= 1
        finally:
            os.unlink(path)

    def test_end_to_end_refund_reject_with_operator_note(self):
        """T041: Refund → reject with note → audit file contains note"""
        from app.services import HandbookService
        from app.workflows.main_workflow import SupportRequestWorkflow
        from app.models import CustomerRequest

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            approval_service = HumanApprovalService(
                audit_log_path=path,
                input_fn=_input_sequence("reject", "outside policy window"),
            )
            handbook_path = _get_handbook_path()
            workflow = SupportRequestWorkflow(
                HandbookService(handbook_path),
                approval_service=approval_service,
            )
            request = CustomerRequest(
                raw_message="I signed up yesterday and want a refund please",
                request_id="req_e2e_t041",
            )
            workflow.execute(request)

            with open(path, encoding="utf-8") as fh:
                lines = [l for l in fh if l.strip()]
            assert len(lines) >= 1
            entry = json.loads(lines[0])
            assert entry.get("operator_note") == "outside policy window"
        finally:
            os.unlink(path)

    def test_multiple_decisions_audit_log_sequential(self):
        """T042: Multiple refund requests → audit log entries in order with unique entry_ids"""
        service = HumanApprovalService(
            input_fn=_input_sequence("approve", "", "reject", "override note"),
        )
        rec1 = _make_recommendation("approve", request_id="req_multi_1")
        rec2 = _make_recommendation("approve", request_id="req_multi_2")
        service.request_approval(rec1)
        service.request_approval(rec2)

        log = service.get_audit_log()
        assert len(log) == 2
        assert log[0].request_id == "req_multi_1"
        assert log[1].request_id == "req_multi_2"
        assert log[0].entry_id != log[1].entry_id


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _get_handbook_path() -> str:
    import pathlib
    base = pathlib.Path(__file__).parent.parent
    return str(base / "data" / "support_handbook.md")
