"""Response generation agent"""
import re

from app.models import WorkflowState, SupportResponse, ClassificationResult, PolicyEvaluation, ClarificationRequest
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
            raw_message = (request.raw_message or "").strip()

            # Keep greetings conversational rather than dumping handbook content.
            if self._is_greeting_only(raw_message) or self._is_capability_question(raw_message):
                response_text = (
                    "Hi! I can help with plan and feature questions, refunds, cancellations, "
                    "billing issues, and escalation requests when needed. "
                    "Tell me what happened and I will guide you based on our support handbook."
                )
            else:
                relevant_sections = self._find_relevant_sections(raw_message)
                if relevant_sections:
                    best_section, best_content = relevant_sections[0]
                    snippet = self._make_snippet(best_content)
                    response_text = (
                        f"Thanks for your question. Based on our '{best_section}' policy:\n\n"
                        f"{snippet}\n\n"
                        "If you share a little more detail, I can give a more specific answer."
                    )
                    handbook_citations = [snippet]
                    cited_policies = [best_section]
                else:
                    response_text = (
                        "Thanks for reaching out. I can help with refunds, cancellations, "
                        "billing questions, and plan/features. "
                        "Could you share a bit more detail so I can answer precisely?"
                    )
            
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
        clarification = ClarificationRequest.from_missing_fields(
            request_id=request.request_id,
            missing_fields=policy_eval.clarification_needed_fields,
        )
        questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(clarification.questions)])
        response_text = (
            f"Thank you for reaching out. I'd like to help you, but I need a bit more information:\n\n"
            f"{questions_text}\n\n"
            f"{clarification.context_why_needed}"
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

    def _is_greeting_only(self, message: str) -> bool:
        """Return True when the message is only a short greeting."""
        cleaned = re.sub(r"[^a-zA-Z\s]", "", message).strip().lower()
        return cleaned in {
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
        }

    def _is_capability_question(self, message: str) -> bool:
        """Detect generic "what can you do" questions."""
        msg = message.lower()
        return any(
            phrase in msg
            for phrase in [
                "how can you help",
                "what can you do",
                "what do you do",
                "can you help me",
            ]
        )

    def _find_relevant_sections(self, message: str) -> list[tuple[str, str]]:
        """Rank handbook sections by overlap with message keywords."""
        tokens = re.findall(r"[a-zA-Z]{4,}", message.lower())
        stop_words = {
            "what",
            "when",
            "where",
            "which",
            "about",
            "please",
            "would",
            "could",
            "thanks",
            "hello",
        }
        keywords = [t for t in tokens if t not in stop_words]

        section_scores: list[tuple[int, str, str]] = []
        for section_name, section_content in self.handbook.get_all_sections().items():
            haystack = f"{section_name} {section_content}".lower()
            score = sum(1 for kw in keywords if kw in haystack)
            if score > 0:
                section_scores.append((score, section_name, section_content))

        section_scores.sort(key=lambda x: x[0], reverse=True)
        return [(name, content) for _, name, content in section_scores[:2]]

    def _make_snippet(self, content: str, max_len: int = 260) -> str:
        """Create a readable one-paragraph snippet for customer-facing responses."""
        normalized = re.sub(r"\s+", " ", content).strip()
        return normalized[:max_len].rstrip() + ("..." if len(normalized) > max_len else "")
