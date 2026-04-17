"""Intent classification service"""
import re
from typing import Optional
from app.models import CustomerRequest, ClassificationResult


class FastClassifier:
    """Fast regex/keyword-based intent classification"""
    
    # Keyword patterns for each intent
    REFUND_KEYWORDS = re.compile(r'\b(refund|money back|charged|overcharged|charged twice|double charge|overcharge|billing error|charge back|wrong amount)\b', re.IGNORECASE)
    CANCEL_KEYWORDS = re.compile(r'\b(cancel|terminate|unsubscribe|close account)\b', re.IGNORECASE)
    ESCALATION_KEYWORDS = re.compile(r'\b(manager|supervisor|lawyer|legal|gdpr|chargeback|regulator|ridiculous|unacceptable|thieves|fraud)\b', re.IGNORECASE)
    
    def classify(self, request: CustomerRequest) -> ClassificationResult:
        """Classify customer request intent using fast rules
        
        Args:
            request: Customer request to classify
        
        Returns:
            ClassificationResult with intent and confidence
        """
        message = request.raw_message.strip()
        message_lower = message.lower()
        
        if not message:
            return ClassificationResult(
                request_id=request.request_id,
                classified_intent="escalation_needed",
                confidence_score=0.95,
                reasoning="Empty message - cannot process",
                needs_policy_check=False,
                escalation_reason="empty_request"
            )
        
        # Check escalation first (highest priority)
        if self.ESCALATION_KEYWORDS.search(message):
            return ClassificationResult(
                request_id=request.request_id,
                classified_intent="escalation_needed",
                confidence_score=0.90,
                reasoning="Message contains escalation keywords (manager/lawyer/legal threat)",
                needs_policy_check=False,
                requires_customer_context=False,
                escalation_reason="escalation_keywords_detected"
            )
        
        # Check cancelation
        if self.CANCEL_KEYWORDS.search(message):
            # But check if it's a question ("should I cancel?") vs. explicit request
            if any(word in message_lower for word in ["should i", "should we", "wondering if", "thinking about"]):
                # It's advisory, not explicit cancel
                return ClassificationResult(
                    request_id=request.request_id,
                    classified_intent="simple_question",
                    confidence_score=0.85,
                    reasoning="Contains cancel keywords but phrased as a question, not a request",
                    needs_policy_check=True,
                    requires_customer_context=False
                )
            else:
                # Explicit cancellation
                return ClassificationResult(
                    request_id=request.request_id,
                    classified_intent="cancellation_request",
                    confidence_score=0.92,
                    reasoning="Message explicitly requests account cancellation",
                    needs_policy_check=True,
                    requires_customer_context=True
                )
        
        # Check refund
        if self.REFUND_KEYWORDS.search(message):
            return ClassificationResult(
                request_id=request.request_id,
                classified_intent="refund_request",
                confidence_score=0.88,
                reasoning="Message contains refund-related keywords",
                needs_policy_check=True,
                requires_customer_context=True
            )

        # Very short or greeting-only messages are low-signal; allow LLM fallback.
        greeting_only = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
        if message_lower in greeting_only or len(message_lower) <= 10:
            return ClassificationResult(
                request_id=request.request_id,
                classified_intent="simple_question",
                confidence_score=0.68,
                reasoning="Message is very short/greeting-only; low intent confidence",
                needs_policy_check=True,
                requires_customer_context=False,
            )

        # Ambiguous wording: keep fast path but mark low confidence for LLM fallback.
        ambiguous_markers = [
            "not sure",
            "i think",
            "maybe",
            "what is going on",
            "can someone check",
            "not really sure",
        ]
        if any(marker in message_lower for marker in ambiguous_markers):
            return ClassificationResult(
                request_id=request.request_id,
                classified_intent="simple_question",
                confidence_score=0.72,
                reasoning="Ambiguous intent markers detected; eligible for LLM fallback",
                needs_policy_check=True,
                requires_customer_context=False,
            )

        # Mixed intent cues (e.g., mentions both cancel and refund) should defer to LLM.
        if self.CANCEL_KEYWORDS.search(message) and self.REFUND_KEYWORDS.search(message):
            return ClassificationResult(
                request_id=request.request_id,
                classified_intent="simple_question",
                confidence_score=0.74,
                reasoning="Mixed refund/cancellation cues detected; eligible for LLM fallback",
                needs_policy_check=True,
                requires_customer_context=False,
            )
        
        # Default: simple question
        return ClassificationResult(
            request_id=request.request_id,
            classified_intent="simple_question",
            confidence_score=0.76,
            reasoning="General question without explicit intent keywords; eligible for LLM fallback",
            needs_policy_check=True,
            requires_customer_context=False
        )


class LLMClassifier:
    """LLM-based classifier for ambiguous cases (fallback)"""
    
    def __init__(self, foundry_client):
        """Initialize with Foundry client
        
        Args:
            foundry_client: FoundryClient instance for LLM calls
        """
        self.client = foundry_client
        self.system_prompt = """You are a customer support intent classifier. 
        
Classify the customer message into ONE of these categories:
- simple_question: General product question or support inquiry
- refund_request: Customer asking for a refund or money back
- cancellation_request: Customer wants to cancel/close their account
- escalation_needed: Customer is angry, demanding escalation, or mentions legal action

Respond with ONLY the category name, nothing else."""
    
    async def classify(self, request: CustomerRequest) -> ClassificationResult:
        """Classify using LLM
        
        Args:
            request: Customer request to classify
        
        Returns:
            ClassificationResult from LLM
        """
        try:
            response = await self.client.complete(
                prompt=f"Customer message:\n\n{request.raw_message}",
                system=self.system_prompt,
                temperature=0.3
            )
            
            intent = response.strip().lower().replace('_needed', '_needed')
            
            valid_intents = ['simple_question', 'refund_request', 'cancellation_request', 'escalation_needed']
            if intent not in valid_intents:
                intent = 'simple_question'  # Fallback
            
            return ClassificationResult(
                request_id=request.request_id,
                classified_intent=intent,
                confidence_score=0.78,
                reasoning=f"LLM classification (fallback): {intent}",
                needs_policy_check=intent != 'escalation_needed',
                requires_customer_context=intent in ['refund_request', 'cancellation_request']
            )
        except Exception as e:
            # Fallback to simple_question on error
            return ClassificationResult(
                request_id=request.request_id,
                classified_intent="simple_question",
                confidence_score=0.50,
                reasoning=f"LLM classification failed: {e}; defaulting to question",
                needs_policy_check=True,
                requires_customer_context=False
            )
