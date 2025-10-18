"""
Script Writer module - generates audio scripts from solutions
"""
from utils.llm_client import LLMClient
from utils.prompt_loader import PromptLoader
from utils.file_manager import FileManager
import config
import re


class ScriptWriter:
    """Generates audio scripts for mathematical explanations"""
    
    def __init__(self, llm_client: LLMClient, prompt_loader: PromptLoader):
        """
        Initialize the script writer
        
        Args:
            llm_client: LLM client instance
            prompt_loader: Prompt loader instance
        """
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.system_prompt = self.prompt_loader.load_prompt(config.SCRIPT_WRITER_PROMPT_PATH)
    
    def write_script(self, solution: str, file_manager: FileManager) -> str:
        """
        Generate audio script from solution
        
        Args:
            solution: The approved mathematical solution
            file_manager: File manager for saving outputs
        
        Returns:
            Audio script as string
        """
        print(f"\n{'='*60}")
        print(f"SCRIPT WRITER")
        print(f"{'='*60}")
        
        script = self.llm_client.generate_response(
            system_prompt=self.system_prompt,
            query=solution,
            temperature=config.TEMPERATURE_SCRIPT_WRITER
        )
        
        # Save full script
        filepath = file_manager.save_text(script, 'audio_script.txt', 'script')
        print(f"✓ Audio script saved: {filepath}")
        
        # Parse and save individual segments
        segments = self._parse_segments(script)
        self._save_segments(segments, file_manager)
        
        print(f"✓ Parsed {len(segments)} audio segments")
        
        return script
    
    def _parse_segments(self, script: str) -> list[dict]:
        """
        Parse script into individual segments
        
        Args:
            script: Full audio script text
        
        Returns:
            List of segment dictionaries with 'number', 'audio', 'visual_cue'
        """
        segments = []
        
        # Pattern to match segments: [SEGMENT N]
        segment_pattern = r'\[SEGMENT\s+(\d+)\].*?\n(.*?)(?=\[SEGMENT|\Z)'
        matches = re.finditer(segment_pattern, script, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            segment_num = int(match.group(1))
            segment_content = match.group(2).strip()
            
            # Extract AUDIO and VISUAL_CUE
            audio_match = re.search(r'AUDIO:\s*(.*?)(?=VISUAL_CUE:|$)', segment_content, re.DOTALL | re.IGNORECASE)
            visual_match = re.search(r'VISUAL_CUE:\s*(.*?)(?=$)', segment_content, re.DOTALL | re.IGNORECASE)
            
            audio = audio_match.group(1).strip() if audio_match else ""
            visual_cue = visual_match.group(1).strip() if visual_match else ""
            
            segments.append({
                'number': segment_num,
                'audio': audio,
                'visual_cue': visual_cue
            })
        
        return segments
    
    def _save_segments(self, segments: list[dict], file_manager: FileManager):
        """Save individual segments to files"""
        # Save as JSON
        file_manager.save_json(segments, 'segments.json', 'script')
        
        # Save individual text files for each audio segment
        for segment in segments:
            filename = f"segment_{segment['number']:02d}_audio.txt"
            file_manager.save_text(segment['audio'], filename, 'audio')
            
            filename = f"segment_{segment['number']:02d}_visual.txt"
            file_manager.save_text(segment['visual_cue'], filename, 'script')
