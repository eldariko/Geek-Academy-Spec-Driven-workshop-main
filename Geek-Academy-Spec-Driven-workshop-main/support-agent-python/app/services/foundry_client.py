"""Foundry LLM client wrapper"""
import os
from typing import Optional
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential


class FoundryClient:
    """Wrapper around Azure Foundry LLM client"""
    
    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        """Initialize Foundry client
        
        Args:
            api_key: Foundry API key (defaults to FOUNDRY_API_KEY env var)
            endpoint: Foundry endpoint URL (defaults to FOUNDRY_ENDPOINT env var)
        
        Raises:
            ValueError: If API key is not provided or found in environment
        """
        self.api_key = api_key or os.getenv("FOUNDRY_API_KEY")
        self.endpoint = endpoint or os.getenv("FOUNDRY_ENDPOINT", "")
        
        if not self.api_key:
            raise ValueError(
                "FOUNDRY_API_KEY not found. Please set it as an environment variable "
                "or pass it to FoundryClient.__init__()"
            )
        
        # Initialize the Azure client
        try:
            self.client = ChatCompletionsClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key) if self.endpoint else None
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Foundry client: {e}")
    
    async def complete(self, prompt: str, system: Optional[str] = None, temperature: float = 0.7) -> str:
        """Call Foundry LLM to generate a completion
        
        Args:
            prompt: The user prompt
            system: Optional system message
            temperature: Temperature for generation (0.0-1.0)
        
        Returns:
            Generated text from the LLM
        """
        try:
            messages = []
            
            if system:
                messages.append({
                    "role": "system",
                    "content": system
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            response = self.client.complete(
                messages=messages,
                temperature=temperature
            )
            
            if response.choices:
                return response.choices[0].message.content or ""
            
            return ""
        except Exception as e:
            raise RuntimeError(f"LLM call failed: {e}")
    
    def complete_sync(self, prompt: str, system: Optional[str] = None, temperature: float = 0.7) -> str:
        """Synchronous wrapper for complete() — useful for non-async contexts
        
        Args:
            prompt: The user prompt
            system: Optional system message
            temperature: Temperature for generation
        
        Returns:
            Generated text from the LLM
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.complete(prompt, system, temperature))
