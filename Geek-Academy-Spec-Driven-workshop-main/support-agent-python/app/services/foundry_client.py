"""Foundry LLM client wrapper"""
import os
from typing import Optional
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential


class FoundryClient:
    """Wrapper around Azure Foundry LLM client"""
    
    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None, deployment_name: Optional[str] = None):
        """Initialize Foundry client
        
        Args:
            api_key: API key (defaults to AZURE_OPENAI_API_KEY, then legacy FOUNDRY_API_KEY)
            endpoint: Endpoint URL (defaults to AZURE_OPENAI_ENDPOINT, then legacy FOUNDRY_ENDPOINT)
            deployment_name: Deployment/model name (defaults to AZURE_OPENAI_DEPLOYMENT_NAME)
        
        Raises:
            ValueError: If API key or endpoint is not provided or found in environment
        """
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("FOUNDRY_API_KEY")
        self.endpoint = (endpoint or os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT", "")).strip()
        self.deployment_name = deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "").strip()
        
        if not self.api_key:
            raise ValueError(
                "AZURE_OPENAI_API_KEY not found. Please set it as an environment variable "
                "or pass it to FoundryClient.__init__()"
            )

        if not self.endpoint:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT not found. Please set it as an environment variable "
                "or pass it to FoundryClient.__init__()"
            )

        self.endpoint = self._normalize_endpoint(self.endpoint, self.deployment_name)
        
        # Initialize the Azure client
        try:
            self.client = ChatCompletionsClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key),
                retry_total=0,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Foundry client: {e}")

    def _normalize_endpoint(self, endpoint: str, deployment_name: str) -> str:
        """Normalize endpoint for Azure OpenAI deployment-scoped chat completions."""
        normalized = endpoint.rstrip("/")

        # Azure OpenAI resource endpoints must include deployment path for this client.
        if ".openai.azure.com" in normalized and "/openai/deployments/" not in normalized:
            if not deployment_name:
                raise ValueError(
                    "AZURE_OPENAI_DEPLOYMENT_NAME is required when using an Azure OpenAI endpoint. "
                    "Add AZURE_OPENAI_DEPLOYMENT_NAME to .env and run again."
                )
            normalized = f"{normalized}/openai/deployments/{deployment_name}"

        return normalized
    
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
            
            response = self.client.complete(messages=messages, temperature=temperature)
            
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
