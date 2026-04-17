"""WorkflowState data model"""
import logging

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Any


logger = logging.getLogger(__name__)


@dataclass
class WorkflowState:
    """Running state of the request through the workflow"""
    
    request_id: str
    request: Optional[Any] = None                           # CustomerRequest object
    classification: Optional[Any] = None                    # ClassificationResult
    policy_evaluation: Optional[Any] = None                 # PolicyEvaluation
    response: Optional[Any] = None                          # SupportResponse
    
    # History for audit trail
    agent_log: List[str] = field(default_factory=list)     # Timestamps + agent outputs
    
    # Error state
    error_occurred: bool = False
    error_message: Optional[str] = None
    error_agent: Optional[str] = None  # Which agent raised the error
    
    def log_agent_step(self, agent_name: str, step_description: str, data: Any = None):
        """Record agent execution for audit and structured logs."""
        timestamp = datetime.now().isoformat()
        entry = f"[{timestamp}] {agent_name}: {step_description}"
        if data:
            entry += f" -> {data}"
        self.agent_log.append(entry)

        logger.info(
            "workflow_step",
            extra={
                "request_id": self.request_id,
                "timestamp": timestamp,
                "agent": agent_name,
                "decision": step_description,
                "data": str(data) if data is not None else "",
            },
        )
    
    @property
    def is_escalable(self) -> bool:
        """Can this request be escalated to human?"""
        return not self.error_occurred or (self.error_message and "escalation" in self.error_message.lower())
