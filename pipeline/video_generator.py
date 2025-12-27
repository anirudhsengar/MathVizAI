"""
Video Generator module - creates Manim visualization scripts
"""
import re
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
    
    def generate_manim_script(self, audio_script: str, file_manager: FileManager, segment_results: list = None) -> str:
        """
        Generate Manim Python script from audio script with phrase-level synchronization.
        
        Args:
            audio_script: The segmented audio script
            file_manager: File manager for saving outputs
            segment_results: List of segment result dicts from TTS with phrase timing:
                            Each contains 'phrases': [{'text', 'start', 'end', 'duration'}, ...]
        
        Returns:
            Manim Python script as string
        """
        print(f"\n{'='*60}")
        print(f"VIDEO GENERATOR (Phrase-Synchronized)")
        print(f"{'='*60}")
        
        # Build phrase-level timing instructions - THIS IS THE KEY CHANGE
        phrase_timing_info = ""
        if segment_results:
            phrase_timing_info = """
=============================================================================
PHRASE-LEVEL ANIMATION SYNCHRONIZATION (CRITICAL - READ CAREFULLY)
=============================================================================

Your animations MUST be synchronized with the audio phrases below.
Each phrase has an EXACT duration - your animation run_time MUST match it.

**THE RULE**: For each phrase, create ONE animation block with run_time equal to the phrase duration.
DO NOT use self.wait() to fill time. The animation should BE the content.

Example for a 3.5 second phrase:
```python
# PHRASE: "Let's explore the parabola." (3.5s)
parabola = FunctionGraph(lambda x: x**2, x_range=[-2, 2], color=BLUE)
self.play(Create(parabola), run_time=3.5)
```

PHRASES BY SEGMENT:
"""
            for seg in segment_results:
                seg_num = seg.get('segment_number', 1)
                duration = seg.get('duration', 0)
                phrases = seg.get('phrases', [])
                
                phrase_timing_info += f"\n--- SEGMENT {seg_num} (Total: {duration:.1f}s, {len(phrases)} phrases) ---\n"
                
                for i, phrase in enumerate(phrases, 1):
                    p_text = phrase.get('text', '')[:80]
                    p_duration = phrase.get('duration', 0)
                    phrase_timing_info += f"  PHRASE {i} ({p_duration:.2f}s): \"{p_text}{'...' if len(phrase.get('text', '')) > 80 else ''}\"\n"
                    phrase_timing_info += f"    → Animation with run_time={p_duration:.2f}\n"
        
        # Base configuration info  
        config_info = f"""
Configuration Requirements:
- Resolution: {config.VIDEO_RESOLUTION}
- Quality: {config.MANIM_QUALITY}
- Format: {config.MANIM_FORMAT}
- Background: {config.VIDEO_BACKGROUND}

Target Audio Script:
{audio_script}
{phrase_timing_info}
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
        
        print(f"  Analyzed Script: Found {segment_count} segments")
        if segment_results:
            total_phrases = sum(len(s.get('phrases', [])) for s in segment_results)
            print(f"  Total Phrases for Synchronization: {total_phrases}")

        scene_enforcement = f"""
CRITICAL ARCHITECTURE - PHRASE-SYNCHRONIZED SCENES:
=====================================================

1. Generate EXACTLY {segment_count} Scene classes: Scene1, Scene2, ... Scene{segment_count}
2. Each SceneN class corresponds to [SEGMENT N] from the audio script
3. **INSIDE each Scene**: Create animations for EACH PHRASE with matching run_time values
4. DO NOT use a single MathVisualization class
5. DO NOT use self.next_section()
6. DO NOT add extra self.wait() calls - let the run_time handle all timing

MANDATORY CODE PATTERN FOR PHRASE SYNCHRONIZATION:
```python
from manim import *

class Scene1(Scene):
    def construct(self):
        # PHRASE 1: "Let's explore the parabola." (3.5s)
        title = Text("The Parabola", color=BLUE).scale(0.9)
        self.play(Write(title), run_time=3.5)
        
        # PHRASE 2: "Notice how it curves upward." (2.8s)
        parabola = FunctionGraph(lambda x: x**2, x_range=[-2, 2], color=YELLOW)
        self.play(FadeOut(title), Create(parabola), run_time=2.8)
        
        # PHRASE 3: "The vertex is at the origin." (3.2s)
        dot = Dot(ORIGIN, color=RED).scale(1.5)
        label = Text("Vertex", color=RED).scale(0.6).next_to(dot, DOWN)
        self.play(
            Create(dot), 
            Write(label),
            Indicate(dot, scale_factor=1.5),
            run_time=3.2
        )
        
        # Each phrase becomes ONE self.play() call with matching run_time
        # This ensures perfect sync with audio

class Scene2(Scene):
    def construct(self):
        # ... Continue for SEGMENT 2's phrases
        ...

# ... Continue for all {segment_count} segments
```

KEY PRINCIPLES:
- ONE self.play() call per phrase
- run_time = phrase duration (to the decimal)
- Chain multiple animations in one play() call to fill time beautifully
- Use transforms, color changes, and movement to keep visuals engaging
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
        
        # Validate multi-scene architecture
        if "class Scene1(Scene):" not in manim_code:
             print("⚠ WARNING: Generated script might be missing 'Scene1' class.")
        
        # Save Manim script
        filepath = file_manager.save_text(manim_code, 'manim_visualization.py', 'video')
        print(f"✓ Manim script saved: {filepath}")
        
        # Save rendering instructions
        instructions = self._generate_rendering_instructions(filepath)
        file_manager.save_text(instructions, 'rendering_instructions.txt', 'video')
        
        return manim_code
    
    def _clean_code(self, code: str) -> str:
        """
        Clean up generated code by removing markdown artifacts and validating syntax.
        Also attempts to fix common truncation issues from LLM output.
        
        Args:
            code: Raw code from LLM
        
        Returns:
            Cleaned and validated code
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
        
        code = code.strip()
        
        # Validate and fix syntax errors
        code = self._validate_and_fix_syntax(code)
        
        return code
    
    def _validate_and_fix_syntax(self, code: str) -> str:
        """
        Validate Python syntax and attempt to fix common LLM truncation issues.
        
        Args:
            code: Python code to validate
        
        Returns:
            Fixed code if possible
        """
        import ast
        
        # First, try to compile the code as-is
        try:
            ast.parse(code)
            return code  # Code is valid
        except SyntaxError as e:
            print(f"⚠ Syntax error detected at line {e.lineno}: {e.msg}")
            print("  Attempting to fix truncation issues...")
        
        # Common fix: Remove incomplete lines at the end
        lines = code.split('\n')
        
        # Try progressively removing lines from the end until code is valid
        for i in range(min(20, len(lines)), 0, -1):
            # Remove last i lines
            truncated_code = '\n'.join(lines[:-i])
            
            # Check if this creates valid Python
            try:
                ast.parse(truncated_code)
                print(f"  ✓ Fixed by removing {i} incomplete line(s) at end")
                
                # Add a placeholder completion for the last Scene if needed
                if 'class Scene' in truncated_code:
                    # Find the last Scene class
                    last_scene_match = None
                    for match in re.finditer(r'class (Scene\d+)\(Scene\):', truncated_code):
                        last_scene_match = match
                    
                    if last_scene_match:
                        last_scene_name = last_scene_match.group(1)
                        # Check if the last scene has a complete construct method
                        last_scene_start = last_scene_match.start()
                        after_last_scene = truncated_code[last_scene_start:]
                        
                        # If construct has no content or is incomplete, add placeholder
                        if 'def construct(self):' in after_last_scene:
                            lines_after = after_last_scene.split('\n')
                            # Check if there's actual content after construct
                            has_content = False
                            for line in lines_after[1:]:  # Skip the class line
                                if 'def construct' in line:
                                    continue
                                if line.strip() and not line.strip().startswith('#'):
                                    has_content = True
                                    break
                            
                            if not has_content:
                                # Add a simple pass or placeholder
                                truncated_code = truncated_code.rstrip() + "\n        # [Truncated - placeholder]\n        self.wait(1)"
                
                return truncated_code
                
            except SyntaxError:
                continue
        
        # If we couldn't fix it automatically, try a more aggressive approach
        # Find the last complete Scene class
        print("  ⚠ Could not auto-fix. Attempting to extract complete scenes only...")
        
        scene_pattern = r'(class Scene\d+\(Scene\):.*?)(?=class Scene\d+\(Scene\):|$)'
        matches = list(re.finditer(scene_pattern, code, re.DOTALL))
        
        if matches:
            complete_scenes = []
            for match in matches:
                scene_code = match.group(1).strip()
                try:
                    # Check if this individual scene is valid
                    test_code = "from manim import *\n\n" + scene_code
                    ast.parse(test_code)
                    complete_scenes.append(scene_code)
                except SyntaxError:
                    # Try to fix this scene
                    lines = scene_code.split('\n')
                    for i in range(1, min(10, len(lines))):
                        try:
                            fixed_scene = '\n'.join(lines[:-i])
                            test_code = "from manim import *\n\n" + fixed_scene
                            ast.parse(test_code)
                            # Add placeholder content if needed
                            if 'self.play' not in fixed_scene and 'self.wait' not in fixed_scene:
                                fixed_scene += "\n        self.wait(1)  # [Truncated placeholder]"
                            complete_scenes.append(fixed_scene)
                            break
                        except SyntaxError:
                            continue
            
            if complete_scenes:
                fixed_code = "from manim import *\n\n" + "\n\n".join(complete_scenes)
                try:
                    ast.parse(fixed_code)
                    print(f"  ✓ Extracted {len(complete_scenes)} complete scene(s)")
                    return fixed_code
                except SyntaxError:
                    pass
        
        # Last resort: return the original with a warning
        print("  ❌ Could not fix syntax errors. Rendering may fail.")
        return code

    
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
