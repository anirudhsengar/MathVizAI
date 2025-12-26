"""
LLM Client wrapper for OpenAI
"""
from openai import OpenAI
from typing import Optional
import config


class LLMClient:
    """Wrapper class for LLM API calls"""
    
    def __init__(self):
        """Initialize the LLM client"""
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
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
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=temperature,
                # top_p=config.TOP_P, # optional, defaults to 1 usually
                max_tokens=max_tokens,
                model=self.model
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            raise Exception(f"LLM API call failed: {str(e)}")
