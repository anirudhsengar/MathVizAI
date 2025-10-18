"""
LLM Client wrapper for Azure AI Inference
"""
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from typing import Optional
import config


class LLMClient:
    """Wrapper class for LLM API calls"""
    
    def __init__(self):
        """Initialize the LLM client"""
        if not config.GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN environment variable not set")
        
        self.client = ChatCompletionsClient(
            endpoint=config.ENDPOINT,
            credential=AzureKeyCredential(config.GITHUB_TOKEN),
        )
        self.model = config.MODEL_NAME
    
    def generate_response(
        self, 
        system_prompt: str, 
        query: str, 
        temperature: float,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a response from the LLM
        
        Args:
            system_prompt: The system prompt defining the AI's role
            query: The user query or input
            temperature: Temperature for response generation
            max_tokens: Maximum tokens for response (defaults to config value)
        
        Returns:
            Generated response as string
        """
        if max_tokens is None:
            max_tokens = config.MAX_TOKENS
        
        try:
            response = self.client.complete(
                messages=[
                    SystemMessage(system_prompt),
                    UserMessage(query),
                ],
                temperature=temperature,
                top_p=config.TOP_P,
                max_tokens=max_tokens,
                model=self.model
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            raise Exception(f"LLM API call failed: {str(e)}")
