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
    
    def generate_manim_script(
        self,
        audio_script: str,
        file_manager: FileManager,
        segment_results: list = None,
        feedback: str | None = None,
        attempt: int = 1,
        scene_evaluator=None,
        max_scene_retries: int | None = None,
    ) -> tuple[str, list[dict], bool]:
        """
        Generate Manim Python script from audio script with phrase-level synchronization.

        Refactored to generate SCENE-BY-SCENE for better quality and robustness.
        Adds attempt/feedback so regenerated drafts can incorporate QA notes.
        Returns the merged script, per-scene evaluation records, and a boolean indicating
        whether all scenes passed per-scene QA.
        """
        print(f"\n{'='*60}")
        print(f"VIDEO GENERATOR (Phrase-Synchronized & Segment-Based) — Attempt {attempt}")
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
    - Generation Attempt: {attempt}

    REVISION FEEDBACK (from visualization QA):
    {feedback.strip() if feedback else 'None. This is the first draft.'}

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
        
        # ------------------------------------------------------------------
        # NEW STRATEGY: GENERATE PER SEGMENT
        # ------------------------------------------------------------------
        
        generated_scenes = []
        scene_eval_records = []
        all_scenes_ok = True

        scene_retry_cap = max_scene_retries or getattr(config, "MAX_VISUAL_RETRIES", 1)
        
        # Prepare segment data map for easy access
        segment_map = {}
        if segment_results:
            for seg in segment_results:
                segment_map[seg.get('segment_number', 1)] = seg

        # Split the audio script into segments text
        # We need the full text for context, but we'll focus on one segment at a time
        
        script_segments = []
        # Simple splitting by [SEGMENT N]
        full_split = re.split(r'(\[SEGMENT\s+\d+\])', audio_script)
        
        # Reconstruct into (header, content) pairs checks
        current_header = ""
        for part in full_split:
            if re.match(r'\[SEGMENT\s+\d+\]', part):
                current_header = part
            elif current_header:
                script_segments.append(current_header + part)
                current_header = ""
        
        if not script_segments:
             # Fallback if no specific tags found
             script_segments = [audio_script]

        # Generate each scene
        for i, segment_text in enumerate(script_segments, 1):
            print(f"\n🎥 GENERATING SCENE {i}/{len(script_segments)}")
            
            # Get timing info for this segment
            match = re.search(r'\[SEGMENT\s+(\d+)\]', segment_text)
            seg_num = int(match.group(1)) if match else i
            seg_data = segment_map.get(seg_num)

            scene_feedback = feedback
            scene_attempt = 1
            scene_approved = False
            last_eval_text = ""
            last_eval_path = ""

            while scene_attempt <= scene_retry_cap:
                # Generate the scene code
                scene_code = self._generate_single_scene(
                    scene_number=i,  # Force sequential Scene1, Scene2...
                    segment_text=segment_text,
                    segment_data=seg_data,
                    latex_instruction=latex_instruction,
                    revision_feedback=scene_feedback,
                    attempt=scene_attempt
                )

                if scene_evaluator:
                    scene_ok, eval_text, eval_path = scene_evaluator(
                        scene_code=scene_code,
                        segment_text=segment_text,
                        segment_data=seg_data,
                        scene_number=i,
                        attempt=scene_attempt,
                        feedback=scene_feedback,
                    )
                else:
                    scene_ok, eval_text, eval_path = True, "", ""

                scene_eval_records.append({
                    "scene_number": i,
                    "segment_number": seg_num,
                    "attempt": scene_attempt,
                    "approved": scene_ok,
                    "evaluation_path": eval_path,
                })

                if scene_ok:
                    scene_approved = True
                    generated_scenes.append(scene_code)
                    break

                last_eval_text = eval_text
                last_eval_path = eval_path
                scene_feedback = f"Scene QA feedback (Attempt {scene_attempt}):\n{eval_text}"
                scene_attempt += 1

            if not scene_approved:
                all_scenes_ok = False
                print(f"✗ Scene {i} not approved after {scene_retry_cap} attempt(s). Aborting remaining scenes.")
                break
        
        # Merge all scenes into one file (may be partial if a scene failed)
        final_script = self._merge_scenes(generated_scenes)
        
        # Save Manim script
        filepath = file_manager.save_text(final_script, 'manim_visualization.py', 'video')
        print(f"✓ Manim script saved: {filepath}")
        
        # Save rendering instructions
        instructions = self._generate_rendering_instructions(filepath)
        file_manager.save_text(instructions, 'rendering_instructions.txt', 'video')
        
        return final_script, scene_eval_records, all_scenes_ok
    
    def _generate_single_scene(
        self,
        scene_number: int,
        segment_text: str,
        segment_data: dict,
        latex_instruction: str,
        revision_feedback: str | None = None,
        attempt: int = 1,
    ) -> str:
        """
        Generate code for a SINGLE Manim Scene with its own RAG loop.
        Uses revision feedback from visualization QA when available.
        """
        # 1. Build Timing Info
        phrase_timing_info = ""
        seg_duration = segment_data.get('duration', 0) if segment_data else 0
        phrases = segment_data.get('phrases', []) if segment_data else []
        
        if phrases:
            phrase_timing_info = f"""
TIMING REQUIREMENTS FOR SCENE {scene_number}:
Total Duration: {seg_duration:.1f}s
Phrase Count: {len(phrases)}

PHRASES TO ANIMATE (You MUST strictly follow these run_times):
"""
            for i, phrase in enumerate(phrases, 1):
                p_text = phrase.get('text', '')[:100]
                p_dur = phrase.get('duration', 0)
                phrase_timing_info += f"  P{i}: ({p_dur:.2f}s) \"{p_text}\"\n"

        # 2. RAG Loop for this specific segment
        final_context = ""
        if self.rag_client:
            print(f"  Starting RAG for Scene {scene_number}...")
            history = f"I need to generate Manim code for this specific segment:\n{segment_text}\n\n{latex_instruction}\n"
            history += "I want visually stunning animations like 3Blue1Brown. I need to be VERY specific."
            
            for i in range(config.MAX_RAG_ITERATIONS):
                react_prompt = f"""
{history}

Current Context:
{final_context if final_context else "None"}

TASK: Plan the visualization for this segment.
ref: Scene {scene_number}

Do you need to search for specific Manim code/examples?
To generate HIGH QUALITY content, you should search!
Active Learning: If you are unsure about how to visualize something complex, SEARCH!

Response Options:
1. "QUERY: <search term>" (Search for code/concepts)
2. "FINISH" (Ready to code)
"""
                try:
                    response = self.llm_client.generate_response(
                        system_prompt="You are an expert Manim developer. Be curious and search for good examples.",
                        query=react_prompt,
                        temperature=0.2
                    ).strip()
                    
                    if response.startswith("QUERY:"):
                        search_term = response.replace("QUERY:", "").strip()
                        print(f"    RAG Retrieval [{i+1}]: {search_term}")
                        retrieved = self.rag_client.retrieve_context(search_term)
                        # Truncate to avoid Rate Limits (TPM)
                        if len(retrieved) > 1500:
                            retrieved = retrieved[:1500] + "... [TRUNCATED]"
                        
                        final_context += f"\n\n--- Context: {search_term} ---\n{retrieved}"
                        history += f"\nUser: Searched '{search_term}'\nSystem: Found info.\n"
                    elif response == "FINISH":
                        break
                    else:
                        break
                except Exception as e:
                    print(f"    RAG Error: {e}")
                    break

        # 3. Generate Scene Code
        scene_classname = f"Scene{scene_number}"
        
        # Load Visual Utils info (Simulated reflection of the file we created)
        visual_utils_info = """
AVAILABLE CUSTOM VISUAL COMPONENTS (library: visual_utils):
You have access to a local library `visual_utils`. USE THESE FUNCTIONS to drastically improve visual quality and SAFETY.

1. `create_neon_graph(axes, function, color=BLUE, glow_radius=0.1, stroke_width=4)`
   - Returns VGroup with a glowing neon effect.
   
2. `create_morphing_grid(rows=5, cols=5, height=4, width=4, color=GRAY)`
   - Returns a stylish grid ready for transformations.
   
3. `create_glowing_text(text_str, font_size=48, color=WHITE, glow_color=BLUE, glow_opacity=0.5)`
   - Returns VGroup of text with a colored blur glow.

4. `create_cyberpunk_box(width=5, height=3, color=TEAL)`
   - Returns a stylish framed box with corner accents.

5. **SAFETY HELPERS (CRITICAL)**:
   - `safe_get_part(mobject, tex_key)`: Safely gets a part of MathTex. Returns original obj if not found.
     - BAD: `tex.get_part_by_tex("x")` (Crashes if "x" missing)
     - GOOD: `safe_get_part(tex, "x")` (Always works)
   - `safe_move_to_part(mobject_to_move, target_mobject, part_tex)`: Safely aligns objects.

USAGE:
from visual_utils import create_neon_graph, safe_get_part, ...
(Already imported in the environment)
"""

        prompt = f"""
GENERATE MANIM CODE FOR: class {scene_classname}(Scene)

    ATTEMPT: {attempt}
    REVISION FEEDBACK:
    {revision_feedback if revision_feedback else 'None. Produce the first draft cleanly and defensively.'}

CONTENT TO VISUALIZE:
{segment_text}

STARTING CONTEXT: {phrase_timing_info}

RETRIEVED KNOWLEDGE:
{final_context}

{visual_utils_info}

{latex_instruction}

STORYBOARD-FIRST STRATEGY:
Before writing code, describe the scene in 3 distinct beats:
1. **Setup:** What objects are initialized? (Style, color, positioning). USE visual_utils components!
2. **Animation Flow:** Exactly how do they move? (Pan camera, transform grid, etc.)
3. **Complexity Check:** List 3 ways this visualization is visually rich (Lighting, Depth, Custom Updaters).

STRICT RULES:
1. Define `class {scene_classname}(Scene):`
2. Implement `def construct(self):`
3. Follow the PHRASE TIMING exactly using `run_time`.
4. **CRITICAL: CLEANUP OLD VISUALS**. 
   - Before showing new concepts, `FadeOut` or `Uncreate` old ones unless they are reused.
5. Provide ONLY the Python code for this class.
6. **SELF-REFLECTION**: After generating, check:
   - Did you use `get_part_by_tex`? REPLACE IT with `safe_get_part`.
   - Did you use simple `Create()`? Replace with organic animations.

Output the code wrapped in ```python ... ```.
"""

        print(f"  Generating code for {scene_classname}...")
        code = self.llm_client.generate_response(
            system_prompt=self.system_prompt,
            query=prompt,
            temperature=config.TEMPERATURE_VIDEO_GENERATOR
        )
        
        return self._clean_code(code)

    def _merge_scenes(self, scene_codes: list) -> str:
        """Merge multiple scene class codes into one file with imports"""
        
        # Standard imports
        final_script = """from manim import *
import numpy as np
import math
import sys
import os

# Add src to path to allow importing visual_utils
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    from visual_utils import *
except ImportError:
    # Fallback if running from a different location
    try:
        sys.path.append(os.path.abspath("src"))
        from visual_utils import *
    except ImportError:
        print("Warning: Could not import visual_utils")

# Generated by MathVizAI
"""
        
        for code in scene_codes:
            # Strip local imports if any generated by mistake
            lines = code.split('\n')
            clean_lines = [l for l in lines if not l.strip().startswith('from manim import') and not l.strip().startswith('import ')]
            
            final_script += "\n\n" + "\n".join(clean_lines)
            
        return final_script
            
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
        
        # Fix common hallucinations
        code = code.replace("np.math.", "math.")
        code = code.replace("numpy.math.", "math.")
        
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
