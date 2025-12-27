"""
Video Generator module - creates Manim visualization scripts
"""
from utils.llm_client import LLMClient
from utils.prompt_loader import PromptLoader
from utils.file_manager import FileManager
from pipeline.rag_client import RAGClient
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
        
        # Initialize RAG client if enabled
        self.rag_client = None
        if getattr(config, 'RAG_ENABLED', False):
            try:
                self.rag_client = RAGClient()
                print("✓ RAG Client initialized for video generation")
            except Exception as e:
                logger.error(f"Failed to initialize RAG Client: {e}")
                print("⚠ RAG Client initialization failed. Continuing without RAG.")
    
    def generate_manim_script(self, audio_script: str, file_manager: FileManager) -> str:
        """
        Generate Manim Python script from audio script
        
        Args:
            audio_script: The segmented audio script
            file_manager: File manager for saving outputs
        
        Returns:
            Manim Python script as string
        """
        print(f"\n{'='*60}")
        print(f"VIDEO GENERATOR (Context-Aware)")
        print(f"{'='*60}")
        
        # Base configuration info
        config_info = f"""
Configuration Requirements:
- Resolution: {config.VIDEO_RESOLUTION}
- Quality: {config.MANIM_QUALITY}
- Format: {config.MANIM_FORMAT}
- Background: {config.VIDEO_BACKGROUND}

Target Audio Script:
{audio_script}
"""
        
        # RAG / ReAct Loop
        final_context = ""
        
        if self.rag_client:
            print(f"Starting RAG ReAct loop (Max iterations: {config.MAX_RAG_ITERATIONS})")
            
            # Initial context gathering loop
            history = f"I need to generate a Manim video for the following script:\n{audio_script}\n\n"
            history += "I have access to a vector store of Manim examples (3b1b style) and general Manim code.\n"
            
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

Please generate the complete, runnable Manim script.
"""
        
        manim_code = self.llm_client.generate_response(
            system_prompt=self.system_prompt,
            query=final_query,
            temperature=config.TEMPERATURE_VIDEO_GENERATOR
        )
        
        # Clean up the code (remove markdown code blocks if present)
        manim_code = self._clean_code(manim_code)
        
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
