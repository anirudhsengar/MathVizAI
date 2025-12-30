"""
Solver module - responsible for solving mathematical problems
"""
from utils.llm_client import LLMClient
from utils.prompt_loader import PromptLoader
from utils.file_manager import FileManager
import config


class MathSolver:
    """Solves mathematical problems using LLM"""
    
    def __init__(self, llm_client: LLMClient, prompt_loader: PromptLoader):
        """
        Initialize the solver
        
        Args:
            llm_client: LLM client instance
            prompt_loader: Prompt loader instance
        """
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.system_prompt = self.prompt_loader.load_prompt(config.SOLVER_PROMPT_PATH)
    
    def solve(self, query: str, file_manager: FileManager, attempt: int = 1) -> str:
        """
        Solve a mathematical problem
        
        Args:
            query: The mathematical problem to solve
            file_manager: File manager for saving outputs
            attempt: Attempt number for retry tracking
        
        Returns:
            Solution as string
        """
        print(f"\n{'='*60}")
        print(f"SOLVER - Attempt {attempt}")
        print(f"{'='*60}")
        print(f"Query: {query[:100]}...")
        
        solution = self.llm_client.generate_response(
            system_prompt=self.system_prompt,
            query=query,
            temperature=config.TEMPERATURE_SOLVER,
            allow_tools=True
        )
        
        # Save solution
        filename = f"solution_attempt_{attempt}.txt"
        filepath = file_manager.save_text(solution, filename, 'solver')
        print(f"✓ Solution saved: {filepath}")
        
        return solution
