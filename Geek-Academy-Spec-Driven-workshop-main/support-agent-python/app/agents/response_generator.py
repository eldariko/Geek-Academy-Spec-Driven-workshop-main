"""Response generation agent"""
from app.models import WorkflowState, SupportResponse, ClassificationResult, PolicyEvaluation
from app.services import HandbookService


class ResponseAgent:
    """Agent responsible for composing customer-facing responses"""
    
    def __init__(self, handbook_service: HandbookService):
        """Initialize response agent
        
        Args:
            handbook_service: HandbookService for policy citations
        """
        self.handbook = handbook_service
    
    def generate(self, workflow_state: WorkflowState) -> SupportResponse:
        """Generate a response based on workflow state
        
        Args:
            workflow_state: WorkflowState with classification and policy eval
        
        Returns:
            SupportResponse ready for customer
        """
        classification = workflow_state.classification
        policy_eval = workflow_state.policy_evaluation
        original_request = workflow_state.request
        
        if not policy_eval:
            raise ValueError("PolicyEvaluation required to generate response")
        
        # Route to appropriate response generator
        if policy_eval.final_decision == "APPROVE":
            return self._generate_approval_response(original_request, policy_eval, classification)
        elif policy_eval.final_decision == "DENY":
            return self._generate_denial_response(original_request, policy_eval)
        elif policy_eval.final_decision == "NEEDS_CLARIFICATION":
            return self._generate_clarification_response(original_request, policy_eval)
        elif policy_eval.final_decision == "ESCALATE":
            return self._generate_escalation_response(original_request, policy_eval)
        else:
            # Fallback
            return self._generate_fallback_response(original_request)
    
    def _generate_approval_response(self, request, policy_eval: PolicyEvaluation, classification: ClassificationResult) -> SupportResponse:
        """Generate approval response"""
        intent = classification.classified_intent
        tone = "professional"
        cited_policies = []
        handbook_citations = []
        
        if intent == "simple_question":
            # For questions, retrieve handbook info
            handbook_sections = self.handbook.get_all_sections()
            section_text = "\n".join(list(handbook_sections.values())[:3])[:300]  # First few sections
            
            response_text = f"Thank you for reaching out. Based on our support handbook:\n\n{section_text}\n\nPlease let me know if you need more information about any of these topics."
            handbook_citations = [section_text[:100]]
            cited_policies = list(handbook_sections.keys())[:3]
            
        elif intent == "refund_request":
            # Generate refund approval response
            if policy_eval.should_apologize:
                response_text = "We sincerely apologize for the error on our end. "
                tone = "empathetic"
            else:
                response_text = "Thank you for reaching out. "
            
            # Extract which rule approved the refund
            approved_rule = None
            for rule in policy_eval.evaluated_rules:
                if rule.decision == "APPROVE":
                    approved_rule = rule
                    break
            
            if approved_rule:
                response_text += f"Your refund has been approved: {approved_rule.rationale}\n\n"
                handbook_citations = [approved_rule.handbook_reference]
                cited_policies = [approved_rule.rule_name]
            else:
                response_text += "Your refund has been approved. "
            
            if policy_eval.should_mention_timeline:
                response_text += "You should see this refund in your original payment method within 5-7 business days (depends on your card issuer)."
            
        elif intent == "cancellation_request":
            response_text = (
                "Thank you for contacting us. If you'd like to proceed with cancellation:\n\n"
                "• Your account will be cancelled immediately in our system\n"
                "• You'll retain access until the end of your current billing period\n"
                "• Your data will be retained for 90 days in case you change your mind\n"
                "• We have a self-serve export tool in your account settings if you'd like to download your data first\n\n"
                "Is there anything I can help clarify before we proceed?"
            )
            handbook_citations = ["Cancellation policy from support handbook"]
            cited_policies = ["cancellation_policy"]
        else:
            response_text = "Thank you for your request. We're reviewing the details and will get back to you shortly."
            handbook_citations = []
            cited_policies = []
        
        return SupportResponse(
            request_id=request.request_id,
            response_text=response_text,
            response_type="answer",
            tone=tone,
            handbook_citations=handbook_citations,
            cited_policies=cited_policies
        )
    
    def _generate_denial_response(self, request, policy_eval: PolicyEvaluation) -> SupportResponse:
        """Generate denial response"""
        # Extract which rule denied the refund
        denial_reason = "policy guidelines do not allow it"
        cited_policies = []
        handbook_citations = []
        
        for rule in policy_eval.evaluated_rules:
            if rule.decision == "DENY":
                denial_reason = rule.rationale
                handbook_citations = [rule.handbook_reference]
                cited_policies = [rule.rule_name]
                break
        
        response_text = (
            f"Thank you for your request. Based on our support policies, "
            f"we're unable to approve this request at this time. Here's why: {denial_reason}. "
            f"If you'd like to discuss this further or have additional context, please let us know."
        )
        
        return SupportResponse(
            request_id=request.request_id,
            response_text=response_text,
            response_type="answer",
            tone="professional",
            handbook_citations=handbook_citations,
            cited_policies=cited_policies
        )
    
    def _generate_clarification_response(self, request, policy_eval: PolicyEvaluation) -> SupportResponse:
        """Generate clarification request response"""
        questions = []
        for field in policy_eval.clarification_needed_fields:
            if field == "charge_date":
                questions.append("Which billing period are you referring to?")
            elif field == "charge_amount":
                questions.append("What amount were you charged?")
            elif field == "error_description":
                questions.append("Can you describe the issue in more detail?")
            else:
                questions.append(f"Can you provide {field}?")
        
        questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
        response_text = (
            f"Thank you for reaching out. I'd like to help you, but I need a bit more information:\n\n"
            f"{questions_text}\n\n"
            f"Once you provide these details, I can process your request right away."
        )
        
        return SupportResponse(
            request_id=request.request_id,
            response_text=response_text,
            response_type="clarification_request",
            tone="professional"
        )
    
    def _generate_escalation_response(self, request, policy_eval: PolicyEvaluation) -> SupportResponse:
        """Generate escalation notice response"""
        return SupportResponse(
            request_id=request.request_id,
            response_text=(
                "Thank you for reaching out. Your request requires special attention, "
                "so I'm escalating it to our support team lead. You can expect to hear back "
                "from them within 24 business hours."
            ),
            response_type="escalation_notice",
            tone="professional",
            escalation_reason=policy_eval.escalation_reason,
            escalation_priority="normal"
        )
    
    def _generate_fallback_response(self, request) -> SupportResponse:
        """Generate fallback response for unexpected states"""
        return SupportResponse(
            request_id=request.request_id,
            response_text=(
                "Thank you for contacting us. We're looking into your request "
                "and will get back to you as soon as possible."
            ),
            response_type="answer",
            tone="professional"
        )
