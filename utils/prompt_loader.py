"""
Utility to load system prompts from files
"""
import os


class PromptLoader:
    """Loads and caches system prompts"""
    
    def __init__(self):
        """Initialize prompt loader"""
        self._cache = {}
    
    def load_prompt(self, filepath: str) -> str:
        """
        Load a system prompt from file
        
        Args:
            filepath: Path to the prompt file
        
        Returns:
            Prompt content as string
        """
        # Check cache first
        if filepath in self._cache:
            return self._cache[filepath]
        
        # Load from file
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Prompt file not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Cache the content
        self._cache[filepath] = content
        
        return content
    
    def reload_prompt(self, filepath: str) -> str:
        """Force reload a prompt from file (bypass cache)"""
        if filepath in self._cache:
            del self._cache[filepath]
        return self.load_prompt(filepath)
