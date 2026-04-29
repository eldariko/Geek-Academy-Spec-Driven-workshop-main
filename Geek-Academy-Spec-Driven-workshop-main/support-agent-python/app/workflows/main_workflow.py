"""Main workflow orchestration"""
import re
import sys
from datetime import datetime
from typing import Optional

from app.models import CustomerRequest, WorkflowState
from app.agents import ClassifierAgent
from app.services import HandbookService, PolicyEngine, SupportOpsMcpClient
from app.agents import ResponseAgent


class SupportRequestWorkflow:
    """Main workflow: Classifier → PolicyEngine → [ApprovalGate] → ResponseAgent"""
    
    def __init__(self, handbook_service: HandbookService, use_llm: bool = False, llm_client=None, approval_service=None, mcp_client: SupportOpsMcpClient | None = None):
        """Initialize workflow
        
        Args:
            handbook_service: HandbookService instance
            use_llm: Whether to use LLM for classifier fallback
            llm_client: Optional Foundry client for LLM
            approval_service: Optional HumanApprovalService for refund approval gate
        """
        self.handbook = handbook_service
        self.classifier = ClassifierAgent(use_llm_fallback=use_llm, llm_client=llm_client)
        self.policy_engine = PolicyEngine(handbook_service)
        self.response_agent = ResponseAgent(handbook_service)
        self.approval_service = approval_service
        self.mcp_client = mcp_client
    
    def execute(self, request: CustomerRequest, allow_clarification_prompt: bool = True) -> WorkflowState:
        """Execute the workflow for a customer request
        
        Args:
            request: CustomerRequest to process
            allow_clarification_prompt: Whether to ask clarification questions interactively
        
        Returns:
            WorkflowState with complete workflow results
        """
        state = WorkflowState(
            request_id=request.request_id,
            request=request
        )
        policy_context: dict = {}
        
        try:
            # Step 1: Classify
            state.log_agent_step("Classifier", "Starting classification")
            classification = self.classifier.classify(request)
            state.classification = classification
            state.log_agent_step("Classifier", f"Classified as {classification.classified_intent}", classification.confidence_score)

            # Host orchestrates MCP lookups and keeps policy ownership local.
            customer_email = self._extract_email_from_message(request.raw_message)
            if customer_email and self.mcp_client is not None:
                lookup = self.mcp_client.get_customer_context(customer_email)
                if lookup.get("ok"):
                    state.customer_context = lookup.get("customer")
                    state.log_agent_step("MCP", "Loaded customer context", state.customer_context.get("customer_id"))
                else:
                    error_payload = lookup.get("error", {"code": "INTERNAL_ERROR", "message": "MCP lookup failed"})
                    state.mcp_errors.append(error_payload)
                    state.log_agent_step("MCP", "Customer context lookup failed", error_payload.get("code"))
            
            # If escalation needed, short-circuit to response
            if classification.escalation_reason:
                state.log_agent_step("Workflow", "Escalation detected, skipping policy engine")
                # Create a minimal policy evaluation for escalation
                from app.models import PolicyEvaluation
                policy_eval = PolicyEvaluation(
                    request_id=request.request_id,
                    intent=classification.classified_intent,
                    final_decision="ESCALATE",
                    escalation_reason=classification.escalation_reason
                )
                state.policy_evaluation = policy_eval
            else:
                # Step 2: Evaluate Policy
                state.log_agent_step("PolicyEngine", "Starting policy evaluation")

                # Build and enrich context from request text for policy evaluation.
                context = self._build_context_from_request(request)
                if state.customer_context:
                    context["customer_id"] = state.customer_context.get("customer_id")
                    context["account_plan"] = state.customer_context.get("plan_type")
                policy_context = context

                policy_eval = self.policy_engine.evaluate(classification, context)
                state.policy_evaluation = policy_eval
                state.log_agent_step("PolicyEngine", f"Decision: {policy_eval.final_decision}", policy_eval.evaluated_rules)

                # If policy needs clarification, ask once and re-run PolicyEngine only.
                if policy_eval.final_decision == "NEEDS_CLARIFICATION" and allow_clarification_prompt:
                    clarification_input = self._collect_clarification_once(policy_eval.clarification_needed_fields)
                    if clarification_input:
                        context = self._merge_clarification_context(context, clarification_input)
                        state.log_agent_step("PolicyEngine", "Re-evaluating with clarification context")
                        policy_eval = self.policy_engine.evaluate(classification, context)
                        state.policy_evaluation = policy_eval
                        state.log_agent_step("PolicyEngine", f"Decision after clarification: {policy_eval.final_decision}", policy_eval.evaluated_rules)

            # Step 2a: Human Approval Gate (refund requests only)
            if (
                classification.classified_intent == "refund_request"
                and not classification.escalation_reason
                and self.approval_service is not None
            ):
                recommendation = self._build_recommendation(state)
                request_text = request.raw_message or ""
                human_decision = self.approval_service.request_approval(recommendation, request_text)
                state.human_decision = human_decision
                state.log_agent_step(
                    "HumanApproval",
                    f"decision={human_decision.decision}",
                    human_decision.overrides_recommendation,
                )

            self._execute_action_tools(state, classification, policy_context)

            # Step 3: Generate Response
            state.log_agent_step("ResponseAgent", "Generating response")
            response = self.response_agent.generate(state)
            state.response = response
            state.log_agent_step("ResponseAgent", f"Response type: {response.response_type}", response.response_text[:50])
            
        except Exception as e:
            state.error_occurred = True
            state.error_message = str(e)
            state.log_agent_step("WorkflowError", f"Error: {e}")
            raise
        
        return state

    def _build_context_from_request(self, request: CustomerRequest) -> dict:
        """Extract policy-relevant context from request and text."""
        context = {
            "account_created_date": request.account_created_date,
            "account_plan": request.account_plan,
            "customer_id": request.customer_id,
            "tone": "neutral",
        }

        message_lower = request.raw_message.lower()

        if "double" in message_lower or "charged twice" in message_lower:
            context["billing_error_type"] = "double_charge"
        elif "wrong amount" in message_lower or "incorrect" in message_lower or "overcharg" in message_lower:
            context["billing_error_type"] = "wrong_amount"
        elif "charged after" in message_lower and "cancel" in message_lower:
            context["billing_error_type"] = "charged_after_cancellation"

        if "outage" in message_lower or "down" in message_lower:
            context["service_outage_during_period"] = True

        amount_match = re.search(r"\$\s*(\d+(?:\.\d{1,2})?)", request.raw_message)
        if amount_match:
            context["charge_amount"] = float(amount_match.group(1))

        # Basic billing period/date hints (month words or explicit date-like strings).
        if re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b", message_lower):
            context["charge_date"] = "billing_period_provided"
        elif re.search(r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b", request.raw_message):
            context["charge_date"] = "date_provided"

        return context

    def _extract_email_from_message(self, message: str) -> str | None:
        match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", message)
        if not match:
            return None
        return match.group(0).strip().lower()

    def _collect_clarification_once(self, missing_fields: list[str]) -> dict | None:
        """Ask one clarification turn in interactive terminals; skip in non-interactive runs."""
        if not missing_fields:
            return None
        if not sys.stdin or not sys.stdin.isatty():
            return None

        print("\nI need one quick clarification to continue:")
        answers: dict[str, str] = {}
        prompts = {
            "charge_date": "Which billing period/date are you referring to? ",
            "charge_amount": "What amount were you charged? (example: 49.99) ",
            "error_description": "Can you describe the issue briefly? ",
        }
        for field in missing_fields:
            prompt = prompts.get(field, f"Please provide {field}: ")
            value = input(prompt).strip()
            if value:
                answers[field] = value
        return answers or None

    def _merge_clarification_context(self, context: dict, clarification_input: dict) -> dict:
        """Merge clarification answers back into policy context."""
        merged = dict(context)
        for key, value in clarification_input.items():
            if key == "charge_amount":
                cleaned = value.replace("$", "").strip()
                try:
                    merged[key] = float(cleaned)
                except ValueError:
                    merged[key] = value
            else:
                merged[key] = value
        return merged

    def _build_recommendation(self, state: WorkflowState):
        """Construct a Recommendation from policy evaluation results."""
        from app.models.approval import Recommendation
        policy_eval = state.policy_evaluation
        suggested = "approve" if policy_eval.final_decision == "APPROVE" else "reject"
        reasoning = " ".join(
            rule.rationale for rule in policy_eval.evaluated_rules if rule.rationale
        ) or policy_eval.final_decision
        rules_applied = [rule.rule_name for rule in policy_eval.evaluated_rules if rule.matches]
        return Recommendation(
            request_id=state.request.request_id,
            suggested_decision=suggested,
            reasoning=reasoning,
            policy_rules_applied=rules_applied,
            generated_at=datetime.now(),
        )

    def _execute_action_tools(self, state: WorkflowState, classification, policy_context: dict) -> None:
        """Execute MCP action tools after host policy and approval decisions are finalized."""
        if self.mcp_client is None:
            return

        policy_eval = state.policy_evaluation
        if not policy_eval:
            return

        customer_id = self._resolve_customer_id(state)

        if policy_eval.final_decision == "ESCALATE":
            reason = policy_eval.escalation_reason or classification.escalation_reason or "manual_review_required"
            if not customer_id:
                state.mcp_errors.append({"code": "INVALID_ARGUMENT", "message": "customer_id required for ticket creation"})
                return
            ticket_response = self.mcp_client.create_ticket(customer_id=customer_id, reason=reason, priority="high")
            if ticket_response.get("ok"):
                state.escalation_ticket = ticket_response.get("ticket")
                ticket_id = (state.escalation_ticket or {}).get("ticket_id")
                state.log_agent_step("MCP", "Escalation ticket created", ticket_id)
            else:
                error_payload = ticket_response.get("error", {"code": "INTERNAL_ERROR", "message": "Ticket creation failed"})
                state.mcp_errors.append(error_payload)
                state.log_agent_step("MCP", "Escalation ticket creation failed", error_payload.get("code"))
            return

        should_record_refund = (
            classification.classified_intent == "refund_request"
            and policy_eval.final_decision == "APPROVE"
            and (state.human_decision is None or state.human_decision.decision == "approve")
        )
        if not should_record_refund:
            return

        if not customer_id:
            state.mcp_errors.append({"code": "INVALID_ARGUMENT", "message": "customer_id required for refund recording"})
            return

        amount = policy_context.get("charge_amount")
        reason = self._build_refund_reason(policy_eval)
        refund_response = self.mcp_client.record_refund_event(customer_id=customer_id, amount=amount, reason=reason)
        if refund_response.get("ok"):
            state.refund_event = refund_response.get("refund_event")
            event_id = (state.refund_event or {}).get("event_id")
            state.log_agent_step("MCP", "Refund event recorded", event_id)
        else:
            error_payload = refund_response.get("error", {"code": "INTERNAL_ERROR", "message": "Refund recording failed"})
            state.mcp_errors.append(error_payload)
            state.log_agent_step("MCP", "Refund event recording failed", error_payload.get("code"))

    def _resolve_customer_id(self, state: WorkflowState) -> str | None:
        context = state.customer_context or {}
        if context.get("customer_id"):
            return context["customer_id"]
        if state.request and state.request.customer_id:
            return state.request.customer_id
        return None

    def _build_refund_reason(self, policy_eval) -> str:
        for rule in policy_eval.evaluated_rules:
            if rule.decision == "APPROVE":
                return rule.rule_name
        return "refund_approved"
