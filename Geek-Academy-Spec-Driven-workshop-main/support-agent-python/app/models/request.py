"""CustomerRequest data model"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict


@dataclass
class CustomerRequest:
    """Initial customer support request"""
    
    # Immutable input
    raw_message: str              # Original customer text
    request_id: str               # Unique ID for tracking
    
    # Optional context (if available)
    timestamp: datetime = field(default_factory=datetime.now)
    customer_id: Optional[str] = None    # Account identifier
    account_created_date: Optional[datetime] = None  # For 30-day window
    account_plan: Optional[str] = None   # "Basic" or "Premium"
    
    # Extracted from message (filled by preprocessing)
    detected_keywords: List[str] = field(default_factory=list)  # Values for keyword-based classification
    tone_indicators: Dict[str, float] = field(default_factory=dict)  # {"angry": 0.8, "urgent": 0.6, ...}
    
    # Processing state
    intent_preliminary: Optional[str] = None  # From fast classifier
    intent_confidence: Optional[float] = None  # 0.0-1.0
    
    def __post_init__(self):
        """Validate request integrity"""
        assert len(self.raw_message) > 0, "raw_message cannot be empty"
        assert len(self.request_id) > 0, "request_id cannot be empty"
