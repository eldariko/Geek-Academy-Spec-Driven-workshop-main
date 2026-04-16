"""Classifier agent implementation"""
from app.models import CustomerRequest, ClassificationResult
from app.services import FastClassifier


class ClassifierAgent:
    """Agent responsible for classifying customer request intent"""
    
    def __init__(self, use_llm_fallback: bool = False, llm_client=None):
        """Initialize classifier agent
        
        Args:
            use_llm_fallback: Whether to use LLM for ambiguous cases
            llm_client: Optional Foundry client for LLM fallback
        """
        self.fast_classifier = FastClassifier()
        self.use_llm_fallback = use_llm_fallback
        self.llm_client = llm_client
    
    def classify(self, request: CustomerRequest) -> ClassificationResult:
        """Classify a customer request
        
        Args:
            request: CustomerRequest to classify
        
        Returns:
            ClassificationResult with determined intent
        """
        result = self.fast_classifier.classify(request)
        
        # If not confident and LLM fallback enabled, try LLM
        if not result.is_confident and self.use_llm_fallback and self.llm_client:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                llm_result = loop.run_until_complete(
                    self._classify_with_llm(request)
                )
                
                # Prefer LLM result if it's more confident
                if llm_result.confidence_score > result.confidence_score:
                    return llm_result
            except Exception:
                pass  # Fall back to fast classifier result
        
        return result
    
    async def _classify_with_llm(self, request: CustomerRequest) -> ClassificationResult:
        """Classify using LLM
        
        Args:
            request: CustomerRequest to classify
        
        Returns:
            ClassificationResult from LLM
        """
        from app.services.intent_classifier import LLMClassifier
        llm_classifier = LLMClassifier(self.llm_client)
        return await llm_classifier.classify(request)
