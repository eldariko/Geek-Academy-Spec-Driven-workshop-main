"""ClarificationRequest data model"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ClarificationRequest:
    """Response Agent requests customer to provide missing information"""
    
    request_id: str
    missing_fields: List[str] = field(default_factory=list)      # ["billing_date", "amount", "error_description"]
    questions: List[str] = field(default_factory=list)           # Customer-friendly questions to ask
    context_why_needed: str = ""                                 # Explanation of why info is needed
    
    # Constraints
    max_retries: int = 1               # Ask once, consolidate next response
    timeout_seconds: Optional[int] = None     # None = wait indefinitely

    @staticmethod
    def question_for_field(field_name: str) -> str:
        """Map a missing field to a customer-friendly question."""
        mappings = {
            "charge_date": "Which billing period are you referring to?",
            "charge_amount": "What amount were you charged?",
            "error_description": "Can you describe the issue in more detail?",
        }
        return mappings.get(field_name, f"Can you provide {field_name}?")

    @classmethod
    def from_missing_fields(cls, request_id: str, missing_fields: List[str]) -> "ClarificationRequest":
        """Create a clarification payload from missing field names."""
        questions = [cls.question_for_field(field) for field in missing_fields]
        return cls(
            request_id=request_id,
            missing_fields=missing_fields,
            questions=questions,
            context_why_needed="I need a bit more information before I can apply the policy correctly.",
        )
    
    def format_for_console(self) -> str:
        """Format clarification request for console UI"""
        output = [self.context_why_needed, ""]
        for i, question in enumerate(self.questions, 1):
            output.append(f"{i}. {question}")
        return "\n".join(output)
