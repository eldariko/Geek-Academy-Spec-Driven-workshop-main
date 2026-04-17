"""Main workflow orchestration"""
import re
import sys

from app.models import CustomerRequest, WorkflowState
from app.agents import ClassifierAgent
from app.services import HandbookService, PolicyEngine
from app.agents import ResponseAgent


class SupportRequestWorkflow:
    """Main workflow: Classifier → PolicyEngine → ResponseAgent"""
    
    def __init__(self, handbook_service: HandbookService, use_llm: bool = False, llm_client=None):
        """Initialize workflow
        
        Args:
            handbook_service: HandbookService instance
            use_llm: Whether to use LLM for classifier fallback
            llm_client: Optional Foundry client for LLM
        """
        self.handbook = handbook_service
        self.classifier = ClassifierAgent(use_llm_fallback=use_llm, llm_client=llm_client)
        self.policy_engine = PolicyEngine(handbook_service)
        self.response_agent = ResponseAgent(handbook_service)
    
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
        
        try:
            # Step 1: Classify
            state.log_agent_step("Classifier", "Starting classification")
            classification = self.classifier.classify(request)
            state.classification = classification
            state.log_agent_step("Classifier", f"Classified as {classification.classified_intent}", classification.confidence_score)
            
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
