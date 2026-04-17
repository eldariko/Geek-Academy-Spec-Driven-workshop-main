"""ClassificationResult data model"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassificationResult:
    """Classifier Agent output: determined intent"""
    
    request_id: str
    classified_intent: str  # One of: "simple_question", "refund_request", "cancellation_request", "escalation_needed"
    confidence_score: float  # 0.0-1.0
    reasoning: str          # Why this classification (for logging)
    
    # Flags for downstream processing
    needs_policy_check: bool = True          # False only for escalation_needed
    requires_customer_context: bool = False   # True for refund/cancel (need account info)
    
    # Escalation signals (if applicable)
    escalation_reason: Optional[str] = None  # e.g., "explicit_manager_request", "legal_mention"
    
    @property
    def is_confident(self) -> bool:
        return self.confidence_score >= 0.8
