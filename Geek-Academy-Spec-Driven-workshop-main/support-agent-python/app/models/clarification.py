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
    
    def format_for_console(self) -> str:
        """Format clarification request for console UI"""
        output = [self.context_why_needed, ""]
        for i, question in enumerate(self.questions, 1):
            output.append(f"{i}. {question}")
        return "\n".join(output)
