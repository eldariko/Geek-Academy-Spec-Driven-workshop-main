"""Orchestrator: coordinates workflow execution"""
import uuid
from datetime import datetime
from app.models import CustomerRequest, SupportResponse
from app.workflows import SupportRequestWorkflow
from app.services import HandbookService


class Orchestrator:
    """High-level orchestrator for request processing"""
    
    def __init__(self, handbook_path: str, use_llm: bool = False, llm_client=None):
        """Initialize orchestrator
        
        Args:
            handbook_path: Path to support handbook
            use_llm: Whether to use LLM for classification
            llm_client: Optional Foundry client
        """
        self.handbook_service = HandbookService(handbook_path)
        self.workflow = SupportRequestWorkflow(
            self.handbook_service,
            use_llm=use_llm,
            llm_client=llm_client
        )
    
    def process(self, raw_message: str, customer_id: str = None) -> SupportResponse:
        """Process a customer request end-to-end
        
        Args:
            raw_message: Raw customer message text
            customer_id: Optional customer ID for context
        
        Returns:
            SupportResponse ready for customer
        """
        # Create request
        request = CustomerRequest(
            raw_message=raw_message,
            request_id=f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            timestamp=datetime.now(),
            customer_id=customer_id
        )
        
        # Execute workflow
        workflow_state = self.workflow.execute(request)
        
        # Return response
        if workflow_state.response:
            return workflow_state.response
        else:
            # Fallback if workflow didn't produce a response
            from app.models import SupportResponse
            return SupportResponse(
                request_id=request.request_id,
                response_text="We're processing your request. Please stand by.",
                response_type="answer",
                tone="professional"
            )
