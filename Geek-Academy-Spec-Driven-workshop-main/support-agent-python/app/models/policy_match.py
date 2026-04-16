"""Policy match and evaluation data models"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PolicyMatch:
    """Single policy rule evaluation"""
    
    rule_name: str              # e.g., "first_month_refund", "double_charge_refund"
    rule_category: str          # "refund" | "cancellation" | "escalation"
    matches: bool               # Does this rule apply?
    decision: str               # "APPROVE", "DENY", "NEEDS_INFO", "ESCALATE"
    rationale: str              # Why this decision
    handbook_reference: str     # Quoted text from handbook
    
    def __repr__(self) -> str:
        return f"[{self.rule_category.upper()}] {self.rule_name}: {self.decision} — {self.rationale}"


@dataclass
class PolicyEvaluation:
    """Policy Agent output: all applicable rules evaluated"""
    
    request_id: str
    intent: str
    evaluated_rules: List[PolicyMatch] = field(default_factory=list)
    
    # Aggregated decision
    final_decision: str = "APPROVE"  # "APPROVE", "DENY", "NEEDS_CLARIFICATION", "ESCALATE"
    clarification_needed_fields: List[str] = field(default_factory=list)  # If NEEDS_CLARIFICATION
    escalation_reason: Optional[str] = None  # If ESCALATE
    
    # Response hints for next agent
    should_apologize: bool = False  # True for billing errors
    should_mention_timeline: bool = False  # True for refunds
    
    @property
    def is_approved(self) -> bool:
        return self.final_decision == "APPROVE"
    
    @property
    def is_denied_cleanly(self) -> bool:
        return self.final_decision == "DENY"
    
    @property
    def requires_escalation(self) -> bool:
        return self.final_decision == "ESCALATE"
    
    @property
    def needs_customer_input(self) -> bool:
        return self.final_decision == "NEEDS_CLARIFICATION"
