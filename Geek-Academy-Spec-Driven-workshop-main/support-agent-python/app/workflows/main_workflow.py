"""Main workflow orchestration"""
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
    
    def execute(self, request: CustomerRequest) -> WorkflowState:
        """Execute the workflow for a customer request
        
        Args:
            request: CustomerRequest to process
        
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
                
                # Build context from request for policy evaluation
                context = {
                    "account_created_date": request.account_created_date,
                    "account_plan": request.account_plan,
                    "customer_id": request.customer_id,
                    "tone": "neutral"  # TODO: Implement tone analysis
                }
                
                # Extract billing error type from message if present
                message_lower = request.raw_message.lower()
                if "double" in message_lower or "charged twice" in message_lower:
                    context["billing_error_type"] = "double_charge"
                elif "wrong amount" in message_lower or "incorrect" in message_lower:
                    context["billing_error_type"] = "wrong_amount"
                elif "charged after" in message_lower and "cancel" in message_lower:
                    context["billing_error_type"] = "charged_after_cancellation"
                
                # Extract service outage indicator
                if "outage" in message_lower or "down" in message_lower:
                    context["service_outage_during_period"] = True
                
                policy_eval = self.policy_engine.evaluate(classification, context)
                state.policy_evaluation = policy_eval
                state.log_agent_step("PolicyEngine", f"Decision: {policy_eval.final_decision}", policy_eval.evaluated_rules)
            
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
