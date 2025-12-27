"""
Video Generator module - creates Manim visualization scripts
"""
from utils.llm_client import LLMClient
from utils.prompt_loader import PromptLoader
from utils.file_manager import FileManager
from pipeline.rag_client import RAGClient
from pipeline.video_renderer import VideoRenderer
import config
import logging

logger = logging.getLogger(__name__)

class VideoGenerator:
    """Generates Manim Python scripts for mathematical visualizations"""
    
    def __init__(self, llm_client: LLMClient, prompt_loader: PromptLoader):
        """
        Initialize the video generator
        
        Args:
            llm_client: LLM client instance
            prompt_loader: Prompt loader instance
        """
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.system_prompt = self.prompt_loader.load_prompt(config.VIDEO_GENERATOR_PROMPT_PATH)
        self.video_renderer = VideoRenderer()
        self.system_prompt = self.prompt_loader.load_prompt(config.VIDEO_GENERATOR_PROMPT_PATH)
        
        # Initialize RAG client if enabled
        self.rag_client = None
        if getattr(config, 'RAG_ENABLED', False):
            try:
                self.rag_client = RAGClient()
                print("✓ RAG Client initialized for video generation")
            except Exception as e:
                logger.error(f"Failed to initialize RAG Client: {e}")
                print("⚠ RAG Client initialization failed. Continuing without RAG.")
    
    def generate_manim_script(self, audio_script: str, file_manager: FileManager, audio_metadata: list = None) -> str:
        """
        Generate Manim Python script from audio script
        
        Args:
            audio_script: The segmented audio script
            file_manager: File manager for saving outputs
            audio_metadata: Optional list of dicts containing 'duration' for each segment
        
        Returns:
            Manim Python script as string
        """
        print(f"\n{'='*60}")
        print(f"VIDEO GENERATOR (Context-Aware)")
        print(f"{'='*60}")
        
        # Format audio duration info if available
        duration_info = ""
        if audio_metadata:
            duration_info = "\nAUDIO TIMINGS (CRITICAL: You MUST fill these exact durations):\n"
            duration_info += "Strategies to fill time:\n"
            duration_info += "1. Use `run_time=2` or `run_time=3` for complex writes/draws.\n"
            duration_info += "2. Add `self.wait(1)` or `self.wait(2)` BETWEEN animations, not just at the end.\n"
            duration_info += "3. If the audio is long, break the animation into smaller steps.\n"
            for i, meta in enumerate(audio_metadata):
                duration = meta.get('duration', 0)
                duration_info += f"- Segment {i+1}: {duration:.2f} seconds\n"
        
        # Base configuration info
        config_info = f"""
Configuration Requirements:
- Resolution: {config.VIDEO_RESOLUTION}
- Quality: {config.MANIM_QUALITY}
- Format: {config.MANIM_FORMAT}
- Background: {config.VIDEO_BACKGROUND}

Target Audio Script:
{audio_script}
{duration_info}
"""

        # Check LaTeX availability dynamically
        is_latex_available = self.video_renderer.check_latex_availability()
        
        latex_instruction = ""
        if is_latex_available:
            latex_instruction = f"""
LATEX AVAILABLE: YES
- Use `MathTex` for all mathematical expressions.
- You can use standard LaTeX syntax like `\\frac{{a}}{{b}}`, `\\int`, etc.
- Example: `MathTex(r"a^2 + b^2 = c^2")`
"""
        else:
            latex_instruction = f"""
LATEX AVAILABLE: NO (CRITICAL)
- DO NOT USE `MathTex` or `Tex`. It will cause a crash.
- Use `Text` for EVERYTHING.
- For math, approximate with text: `Text("x^2 + y^2 = r^2")`
- Focus on color and placement since you cannot use nice rendering.
"""

        # Extract segment count to enforce strict 1:1 mapping
        import re
        segment_matches = re.findall(r'\[SEGMENT\s+(\d+)\]', audio_script)
        segment_count = len(segment_matches) if segment_matches else 1
        
        print(f"  Analzyed Script: Found {segment_count} segments")
        
        scene_enforcement = """
CRITICAL SCENE RULES:
1. Every scene MUST be a separate class (Scene1, Scene2, etc.).
2. Every scene MUST inherit from Scene (not MovingCameraScene, etc.).
3. Every scene MUST have a `def construct(self):` method.
4. Do NOT use `if __name__ == "__main__":`.
5. Do NOT use deprecated functions like ShowCreation; use Create instead.
6. Ensure all assets (e.g., SVG, images) are generated or available.
"""
        
        # RAG / ReAct Loop
        final_context = ""
        
        if self.rag_client:
            print(f"Starting RAG ReAct loop (Max iterations: {config.MAX_RAG_ITERATIONS})")
            
            # Initial context gathering loop
            history = f"I need to generate a Manim video for the following script:\n{audio_script}\n\n{latex_instruction}\n"
            history += "I have access to a vector store of Manim examples (3b1b style) and general Manim code.\n"
            history += "I want to create visually stunning animations like 3Blue1Brown.\n"
            
            for i in range(config.MAX_RAG_ITERATIONS):
                # Ask LLM if it needs context
                react_prompt = f"""
{history}

Current Context Accumulated:
{final_context if final_context else "None"}

Do you need to search for any specific Manim code examples, styles, or functions to implement this video script effectively?
If YES, respond with exactly: "QUERY: <search term>"
If NO (you have enough info to generate the full script), respond with exactly: "FINISH"

Example: "QUERY: how to animate neural network layers"
"""
                response = self.llm_client.generate_response(
                    system_prompt="You are an expert Manim developer planning a script. You can search a codebase for examples.",
                    query=react_prompt,
                    temperature=0.1 # Low temp for decision making
                ).strip()
                
                if response.startswith("QUERY:"):
                    search_term = response.replace("QUERY:", "").strip()
                    print(f"  Refining Context [{i+1}/{config.MAX_RAG_ITERATIONS}]: {search_term}")
                    
                    retrieved_info = self.rag_client.retrieve_context(search_term)
                    final_context += f"\n\n--- Context for '{search_term}' ---\n{retrieved_info}"
                    history += f"\nUser (Self): Searched for '{search_term}'\nSystem: Found relevant code examples.\n"
                    
                elif response == "FINISH":
                    print("  Context gathering complete.")
                    break
                else:
                    # Fallback if LLM chats effectively
                    print(f"  LLM Decision: {response}")
                    if "QUERY" in response:
                        # Try to extract loosely
                        pass 
                    break
        
        # Generate Final Script
        print("\nGenerating final Manim script...")
        
        final_query = f"""
{config_info}

RETRIEVED CONTEXT / EXAMPLES:
{final_context}

{scene_enforcement}

{latex_instruction}

Please generate the complete, runnable Manim script.
"""
        
        manim_code = self.llm_client.generate_response(
            system_prompt=self.system_prompt,
            query=final_query,
            temperature=config.TEMPERATURE_VIDEO_GENERATOR
        )
        
        # Clean up the code (remove markdown code blocks if present)
        manim_code = self._clean_code(manim_code)
        
        # Validate scene count
        scenes_found = len(re.findall(r'class\s+Scene(\d+)\s*\(Scene\):', manim_code))
        if scenes_found != segment_count:
            print(f"⚠ WARNING: Generated {scenes_found} scenes, but expected {segment_count}.")
            # We could trigger a retry here, but for now just warn
        else:
            print(f"✓ Validation passed: {scenes_found} scenes generated.")
        
        # Save Manim script
        filepath = file_manager.save_text(manim_code, 'manim_visualization.py', 'video')
        print(f"✓ Manim script saved: {filepath}")
        
        # Save rendering instructions
        instructions = self._generate_rendering_instructions(filepath)
        file_manager.save_text(instructions, 'rendering_instructions.txt', 'video')
        
        return manim_code
    
    def _clean_code(self, code: str) -> str:
        """
        Clean up generated code by removing markdown artifacts
        
        Args:
            code: Raw code from LLM
        
        Returns:
            Cleaned code
        """
        # Remove markdown code blocks
        if '```python' in code:
            code = code.split('```python')[1]
            if '```' in code:
                code = code.split('```')[0]
        elif '```' in code:
            parts = code.split('```')
            if len(parts) >= 2:
                code = parts[1]
        
        return code.strip()
    
    def _generate_rendering_instructions(self, script_path: str) -> str:
        """
        Generate instructions for rendering the Manim video
        
        Args:
            script_path: Path to the Manim script
        
        Returns:
            Rendering instructions as string
        """
        instructions = f"""
MANIM RENDERING INSTRUCTIONS
{'='*60}

Script Location: {script_path}

To render this video, run one of the following commands:

1. High Quality (1080p60):
   manim -qh -p {script_path} MathVisualization

2. Production Quality (1440p60):
   manim -qk -p {script_path} MathVisualization

3. Preview Quality (480p15):
   manim -ql -p {script_path} MathVisualization

Configuration:
- Resolution: {config.VIDEO_RESOLUTION}
- Quality Flag: -qh (high quality)
- Format: {config.MANIM_FORMAT}

Notes:
- The -p flag opens the video after rendering
- Use -s to render only the last frame (for debugging)
- Output will be in media/videos/ directory by default

To render without opening:
   manim -qh {script_path} MathVisualization

For more options, see: manim --help
"""
        return instructions
