"""Classifier agent implementation"""
import asyncio
import logging

from app.models import CustomerRequest, ClassificationResult
from app.services import FastClassifier


logger = logging.getLogger(__name__)


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
        
        # If low confidence (<0.8) and LLM fallback enabled, try LLM.
        if result.confidence_score < 0.8 and self.use_llm_fallback and self.llm_client:
            try:
                llm_result = asyncio.run(self._classify_with_llm(request))

                if llm_result.reasoning.startswith("LLM classification failed"):
                    logger.warning("llm_fallback_unavailable: %s", llm_result.reasoning)
                
                # Prefer LLM result if it's more confident
                if llm_result.confidence_score > result.confidence_score:
                    return llm_result
            except Exception as ex:
                logger.warning("llm_fallback_failed: %s", ex)
                # Fall back to fast classifier result
        
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
