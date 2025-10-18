"""
Orchestrator - manages the complete pipeline
"""
from utils.llm_client import LLMClient
from utils.prompt_loader import PromptLoader
from utils.file_manager import FileManager
from pipeline.solver import MathSolver
from pipeline.evaluator import SolutionEvaluator
from pipeline.script_writer import ScriptWriter
from pipeline.video_generator import VideoGenerator
import config
from datetime import datetime


class PipelineOrchestrator:
    """Orchestrates the complete MathVizAI pipeline"""
    
    def __init__(self):
        """Initialize the orchestrator and all pipeline components"""
        print("\n" + "="*60)
        print("MATHVIZAI - Initializing Pipeline")
        print("="*60)
        
        # Initialize core utilities
        self.llm_client = LLMClient()
        self.prompt_loader = PromptLoader()
        
        # Initialize pipeline components
        self.solver = MathSolver(self.llm_client, self.prompt_loader)
        self.evaluator = SolutionEvaluator(self.llm_client, self.prompt_loader)
        self.script_writer = ScriptWriter(self.llm_client, self.prompt_loader)
        self.video_generator = VideoGenerator(self.llm_client, self.prompt_loader)
        
        print("✓ All components initialized successfully\n")
    
    def process_query(self, query: str) -> dict:
        """
        Process a mathematical query through the complete pipeline
        
        Args:
            query: The mathematical problem to solve
        
        Returns:
            Dictionary with all outputs and metadata
        """
        start_time = datetime.now()
        
        # Initialize file manager for this session
        file_manager = FileManager(query)
        print(f"✓ Session folder created: {file_manager.session_folder}\n")
        
        # Save the original query
        file_manager.save_text(query, 'original_query.txt')
        
        # Phase 1: Solver-Evaluator Loop (retry until correct)
        solution, evaluation = self._solve_with_validation(query, file_manager)
        
        # Phase 2: Generate audio script
        audio_script = self.script_writer.write_script(solution, file_manager)
        
        # Phase 3: Generate Manim video script
        manim_script = self.video_generator.generate_manim_script(audio_script, file_manager)
        
        # Calculate processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Create metadata
        metadata = {
            'query': query,
            'timestamp': start_time.isoformat(),
            'processing_time_seconds': processing_time,
            'session_folder': file_manager.session_folder,
            'outputs': {
                'solution': file_manager.get_path('solution_final.txt', 'solver'),
                'evaluation': file_manager.get_path('evaluation_final.txt', 'evaluator'),
                'audio_script': file_manager.get_path('audio_script.txt', 'script'),
                'manim_script': file_manager.get_path('manim_visualization.py', 'video'),
            }
        }
        
        # Save final solution and evaluation
        file_manager.save_text(solution, 'solution_final.txt', 'solver')
        file_manager.save_text(evaluation, 'evaluation_final.txt', 'evaluator')
        
        # Save metadata
        file_manager.save_metadata(metadata)
        
        # Print summary
        self._print_summary(metadata)
        
        return metadata
    
    def _solve_with_validation(self, query: str, file_manager: FileManager) -> tuple[str, str]:
        """
        Solve problem with validation loop
        
        Args:
            query: Mathematical problem
            file_manager: File manager instance
        
        Returns:
            Tuple of (approved_solution, final_evaluation)
        """
        attempt = 1
        max_retries = config.MAX_SOLVER_RETRIES
        
        while attempt <= max_retries:
            # Generate solution
            solution = self.solver.solve(query, file_manager, attempt)
            
            # Evaluate solution
            is_correct, evaluation = self.evaluator.evaluate(solution, file_manager, attempt)
            
            if is_correct:
                print(f"\n{'='*60}")
                print(f"✓ Solution approved after {attempt} attempt(s)")
                print(f"{'='*60}\n")
                return solution, evaluation
            
            if attempt < max_retries:
                print(f"\nRetrying... (Attempt {attempt + 1}/{max_retries})")
                
                # Provide feedback to solver for next attempt
                query = self._create_retry_query(query, solution, evaluation)
            else:
                print(f"\n{'='*60}")
                print(f"⚠ Maximum retries ({max_retries}) reached")
                print(f"Using last solution despite issues")
                print(f"{'='*60}\n")
                return solution, evaluation
            
            attempt += 1
        
        # Should not reach here, but return last attempt if we do
        return solution, evaluation
    
    def _create_retry_query(self, original_query: str, previous_solution: str, evaluation: str) -> str:
        """
        Create an enhanced query for retry with evaluation feedback
        
        Args:
            original_query: Original problem
            previous_solution: Previous solution attempt
            evaluation: Evaluation feedback
        
        Returns:
            Enhanced query for retry
        """
        retry_query = f"""
Original Problem:
{original_query}

Previous Solution Issues:
{evaluation}

Please solve this problem again, addressing the issues identified in the evaluation above.
Ensure all steps are correct and the proof is rigorous.
"""
        return retry_query
    
    def _print_summary(self, metadata: dict):
        """Print processing summary"""
        print(f"\n{'='*60}")
        print("PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Session Folder: {metadata['session_folder']}")
        print(f"Processing Time: {metadata['processing_time_seconds']:.2f} seconds")
        print(f"\nGenerated Files:")
        for output_type, path in metadata['outputs'].items():
            print(f"  - {output_type}: {path}")
        print(f"\nNext Steps:")
        print(f"  1. Review the solution in: solver/")
        print(f"  2. Check audio script segments in: audio/")
        print(f"  3. Render Manim video from: video/manim_visualization.py")
        print(f"  4. Generate audio using TTS (neuTTS-air) - TO BE IMPLEMENTED")
        print(f"  5. Sync audio and video - TO BE IMPLEMENTED")
        print(f"{'='*60}\n")
