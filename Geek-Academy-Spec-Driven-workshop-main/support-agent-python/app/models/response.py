"""SupportResponse data model"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class SupportResponse:
    """Response Agent output: final customer-facing response"""
    
    request_id: str
    response_text: str              # Main message to customer
    response_type: str              # "answer" | "clarification_request" | "escalation_notice"
    
    # Metadata for logging/audit
    tone: str = "professional"      # "professional", "empathetic", "firm"
    handbook_citations: List[str] = field(default_factory=list)  # Quoted policies applied
    cited_policies: List[str] = field(default_factory=list)  # Policy names (e.g., "first_month_refund")
    
    # Actions (if any)
    recommended_action: Optional[str] = None  # "issue_refund", "cancel_account", "create_ticket"
    action_parameters: Dict[str, Any] = field(default_factory=dict)  # {"amount": 49.99, "reason": "service_outage"}
    
    # Escalation details (if applicable)
    escalation_ticket_id: Optional[str] = None
    escalation_reason: Optional[str] = None
    escalation_priority: Optional[str] = None  # "high", "normal"
    
    def __repr__(self) -> str:
        return f"[{self.response_type.upper()}] {self.response_text[:50]}..."
