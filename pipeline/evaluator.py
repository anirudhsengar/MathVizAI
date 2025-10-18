"""
Evaluator module - validates mathematical solutions
"""
from utils.llm_client import LLMClient
from utils.prompt_loader import PromptLoader
from utils.file_manager import FileManager
import config
import re


class SolutionEvaluator:
    """Evaluates and validates mathematical solutions"""
    
    def __init__(self, llm_client: LLMClient, prompt_loader: PromptLoader):
        """
        Initialize the evaluator
        
        Args:
            llm_client: LLM client instance
            prompt_loader: Prompt loader instance
        """
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.system_prompt = self.prompt_loader.load_prompt(config.EVALUATOR_PROMPT_PATH)
    
    def evaluate(self, solution: str, file_manager: FileManager, attempt: int = 1) -> tuple[bool, str]:
        """
        Evaluate a mathematical solution
        
        Args:
            solution: The solution to evaluate
            file_manager: File manager for saving outputs
            attempt: Attempt number for retry tracking
        
        Returns:
            Tuple of (is_correct, evaluation_report)
        """
        print(f"\n{'='*60}")
        print(f"EVALUATOR - Attempt {attempt}")
        print(f"{'='*60}")
        
        evaluation = self.llm_client.generate_response(
            system_prompt=self.system_prompt,
            query=solution,
            temperature=config.TEMPERATURE_EVALUATOR
        )
        
        # Save evaluation
        filename = f"evaluation_attempt_{attempt}.txt"
        filepath = file_manager.save_text(evaluation, filename, 'evaluator')
        print(f"✓ Evaluation saved: {filepath}")
        
        # Parse evaluation to determine if solution is correct
        is_correct = self._parse_evaluation(evaluation)
        
        if is_correct:
            print("✓ Solution APPROVED")
        else:
            print("✗ Solution REJECTED - Issues found")
        
        return is_correct, evaluation
    
    def _parse_evaluation(self, evaluation: str) -> bool:
        """
        Parse evaluation report to determine if solution is correct
        
        Args:
            evaluation: Evaluation report text
        
        Returns:
            True if solution is correct, False otherwise
        """
        evaluation_lower = evaluation.lower()
        
        # Look for overall assessment
        if 'overall assessment:' in evaluation_lower:
            # Extract the assessment line
            assessment_match = re.search(
                r'overall assessment:\s*\[?(correct|incorrect|needs_revision)\]?',
                evaluation_lower
            )
            if assessment_match:
                assessment = assessment_match.group(1)
                return assessment == 'correct'
        
        # Look for final verdict
        if 'final verdict:' in evaluation_lower:
            # Check if "yes" appears in verdict
            verdict_section = evaluation_lower.split('final verdict:')[1]
            # Take first 200 chars of verdict
            verdict_text = verdict_section[:200]
            if 'yes' in verdict_text and 'suitable' in verdict_text:
                return True
        
        # Look for correctness score
        score_match = re.search(r'correctness score:\s*\[?(\d+)', evaluation_lower)
        if score_match:
            score = int(score_match.group(1))
            # Require score of 9 or 10 to pass
            return score >= 9
        
        # Default to False if we can't determine
        return False
