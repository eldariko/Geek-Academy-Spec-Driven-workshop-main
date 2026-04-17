#!/usr/bin/env python3
"""Quick test script for LLM fallback."""

import asyncio
import sys
from app.orchestration.support_request_processor import SupportRequestProcessor

async def test_llm():
    # Create processor with LLM enabled
    processor = SupportRequestProcessor(use_llm_fallback=True)
    
    # Test with an ambiguous message that should trigger LLM fallback (confidence < 0.8)
    test_message = "not sure what's going on with my account"
    print(f"Testing with message: '{test_message}'")
    print("-" * 60)
    
    try:
        result = await processor.process_request(test_message)
        
        print(f"\n✓ SUCCESS - Got response from agent")
        print(f"\nClassification:")
        print(f"  Intent: {result.classification.intent}")
        print(f"  Confidence: {result.classification.confidence_score}")
        print(f"  Reasoning: {result.classification.reasoning[:200]}...")
        
        print(f"\nDecision:")
        print(f"  Action: {result.decision.action}")
        print(f"  Reasoning: {result.decision.reasoning[:200]}...")
        
        print(f"\nResponse:")
        print(f"  {result.response[:300]}...")
        
    except Exception as e:
        print(f"\n✗ FAILED - Error during processing:")
        print(f"  {type(e).__name__}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_llm())
