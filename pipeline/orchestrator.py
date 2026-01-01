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
from pipeline.tts_generator import TTSGenerator
from pipeline.video_renderer import VideoRenderer
from pipeline.video_synchronizer import VideoSynchronizer
import config
from datetime import datetime
import os
import shutil


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
        self.tts_generator = TTSGenerator()
        self.video_renderer = VideoRenderer()
        self.video_synchronizer = VideoSynchronizer()
        
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
        
        # Phase 3: Generate audio files (TTS) - Returns segment results with phrase timing
        segment_results = self._generate_audio(file_manager)
        
        # Extract audio file paths for backward compatibility
        audio_files = [r['audio_file'] for r in segment_results] if segment_results else []
        
        # Phase 4: Generate Manim script
        manim_script = self._generate_manim_script(
            audio_script,
            file_manager,
            segment_results
        )

        # Phase 5: Render videos from Manim script
        rendered_videos = self._render_videos(file_manager, audio_files)
        
        # Phase 6: Synchronize audio and video
        synced_videos, final_video = self._synchronize_audio_video(
            file_manager, audio_files, rendered_videos
        )
        
        # Calculate processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Create metadata
        metadata = {
            'query': query,
            'timestamp': start_time.isoformat(),
            'processing_time_seconds': processing_time,
            'session_folder': file_manager.session_folder,
            'tts_available': self.tts_generator.is_available(),
            'audio_files_generated': len(audio_files) if audio_files else 0,
            'video_rendering_available': self.video_renderer.is_available(),
            'videos_rendered': len(rendered_videos) if rendered_videos else 0,
            'sync_available': self.video_synchronizer.is_available(),
            'segments_synced': len(synced_videos) if synced_videos else 0,
            'final_video': final_video,

            'outputs': {
                'solution': file_manager.get_path('solution_final.txt', 'solver'),
                'evaluation': file_manager.get_path('evaluation_final.txt', 'evaluator'),
                'audio_script': file_manager.get_path('audio_script.txt', 'script'),
                'manim_script': file_manager.get_path('manim_visualization.py', 'video'),

                'audio_files': audio_files if audio_files else [],
                'rendered_videos': rendered_videos if rendered_videos else {},
                'synced_segments': synced_videos if synced_videos else [],
                'final_video': final_video
            }
        }
        
        # Save final solution and evaluation
        file_manager.save_text(solution, 'solution_final.txt', 'solver')
        file_manager.save_text(evaluation, 'evaluation_final.txt', 'evaluator')
        
        # Save metadata
        file_manager.save_metadata(metadata)
        
        # Print summary
        self._print_summary(metadata)
        
        # Cleanup if DEBUG_MODE is False
        if not config.DEBUG_MODE:
            self._perform_cleanup(file_manager, metadata)

        
        return metadata

    def _perform_cleanup(self, file_manager: FileManager, metadata: dict):
        """
        Clean up intermediate files if DEBUG_MODE is False
        
        Args:
            file_manager: File manager instance
            metadata: Session metadata
        """
        if config.DEBUG_MODE:
            return
            
        print(f"\n{'='*60}")
        print("CLEANUP (DEBUG_MODE=False)")
        print(f"{'='*60}")
        
        # Keep track of final video path to ensure we don't delete it
        final_video_path = metadata.get('final_video')
        
        if not final_video_path or not os.path.exists(final_video_path):
            print("⚠ Final video not found. Skipping cleanup to preserve data.")
            return

        print("Removing intermediate files...")

        # List of folders to remove
        folders_to_remove = ['solver', 'evaluator', 'script', 'audio', 'video']
        
        for folder in folders_to_remove:
            folder_path = os.path.join(file_manager.session_folder, folder)
            if os.path.exists(folder_path):
                try:
                    shutil.rmtree(folder_path)
                    # print(f"  - Removed {folder}/")
                except Exception as e:
                    print(f"  ⚠ Failed to remove {folder}/: {e}")
        
        # Remove 'synced' folder in 'final'
        synced_path = os.path.join(file_manager.session_folder, 'final', 'synced')
        if os.path.exists(synced_path):
             try:
                shutil.rmtree(synced_path)
                # print(f"  - Removed final/synced/")
             except Exception as e:
                print(f"  ⚠ Failed to remove final/synced/: {e}")

        # Remove root files like original_query.txt, metadata.json etc
        for filename in os.listdir(file_manager.session_folder):
            file_path = os.path.join(file_manager.session_folder, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    # print(f"  - Removed {filename}")
                except Exception as e:
                    print(f"  ⚠ Failed to remove {filename}: {e}")
                    
        print("✓ Cleanup complete. Only final video preserved.")
        print(f"{'='*60}\n")

    
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
    
    def _generate_audio(self, file_manager: FileManager) -> list:
        """
        Generate audio files from script segments with phrase-level timing.
        
        Args:
            file_manager: File manager instance
        
        Returns:
            List of segment result dictionaries containing:
            - 'audio_file': path to generated audio
            - 'segment_number': segment number
            - 'duration': total duration in seconds
            - 'text': original text
            - 'phrases': list of phrase timing dicts with {text, start, end, duration}
        """
        if not self.tts_generator.is_available():
            print("\n⚠ TTS not available. Skipping audio generation.")
            return []
        
        # Load segments
        segments_path = file_manager.get_path('segments.json', 'script')
        if not os.path.exists(segments_path):
            print(f"✗ Segments file not found: {segments_path}")
            return []
        
        import json
        with open(segments_path, 'r', encoding='utf-8') as f:
            segments = json.load(f)
        
        # Generate audio with phrase timing
        segment_results = self.tts_generator.generate_audio_segments(
            segments=segments,
            file_manager=file_manager
        )
        
        return segment_results

    def _generate_manim_script(
        self,
        audio_script: str,
        file_manager: FileManager,
        segment_results: list,
    ) -> str:
        """Generate Manim script without validation loop."""
        
        manim_script, _, _ = self.video_generator.generate_manim_script(
            audio_script,
            file_manager,
            segment_results=segment_results,
            attempt=1,
            scene_evaluator=None,
        )
        return manim_script
    
    def _render_videos(self, file_manager: FileManager, audio_files: list) -> dict:
        """
        Render Manim videos from the generated script
        
        Args:
            file_manager: File manager instance
            audio_files: List of audio file paths for alignment
        
        Returns:
            Dictionary mapping scene names to video paths
        """
        if not self.video_renderer.is_available():
            print("\n⚠ Manim not available. Skipping video rendering.")
            print("   Install Manim to enable automatic rendering:")
            print("   pip install manim")
            return {}
        
        # Get the Manim script path
        manim_script_path = file_manager.get_path('manim_visualization.py', 'video')
        
        if not os.path.exists(manim_script_path):
            print(f"✗ Manim script not found: {manim_script_path}")
            return {}
        
        # Get the video output folder (create a 'rendered' subfolder)
        video_output_folder = os.path.join(
            file_manager.session_folder,
            'video',
            'rendered'
        )
        
        # Determine quality from config
        quality_map = {
            'low': 'l',
            'medium': 'm',
            'high': 'h',
            '4k': 'k'
        }
        quality = quality_map.get(config.MANIM_QUALITY.lower(), 'h')
        
        # Render all scenes
        if audio_files:
            # Use audio-aligned rendering if audio available
            print(f"\n📎 Rendering with audio alignment ({len(audio_files)} audio segments)")
            rendered_pairs = self.video_renderer.render_with_audio_alignment(
                script_path=manim_script_path,
                audio_segments=audio_files,
                output_folder=video_output_folder,
                quality=quality
            )
            
            # Convert to dict - each scene paired with its audio
            rendered_videos = {f"scene_{i+1}": video for i, (video, audio) in enumerate(rendered_pairs)}
        else:
            # Standard rendering without audio
            rendered_videos = self.video_renderer.render_all_scenes(
                script_path=manim_script_path,
                output_folder=video_output_folder,
                quality=quality
            )
        
        # Save rendering metadata
        if rendered_videos:
            rendering_metadata = {
                'script_path': manim_script_path,
                'output_folder': video_output_folder,
                'quality': config.MANIM_QUALITY,
                'scenes_rendered': len(rendered_videos),
                'videos': rendered_videos,
                'audio_aligned': len(audio_files) > 0
            }
            file_manager.save_json(rendering_metadata, 'rendering_metadata.json', 'video')
        
        return rendered_videos
    
    def _synchronize_audio_video(
        self,
        file_manager: FileManager,
        audio_files: list,
        rendered_videos: dict
    ) -> tuple:
        """
        Synchronize audio and video segments
        
        Args:
            file_manager: File manager instance
            audio_files: List of audio file paths
            rendered_videos: Dictionary of rendered video paths
        
        Returns:
            Tuple of (synced_segments_list, final_video_path)
        """
        if not self.video_synchronizer.is_available():
            print("\n⚠ FFmpeg not available. Skipping audio-video synchronization.")
            print("   Install FFmpeg to enable sync:")
            print("   Windows: choco install ffmpeg")
            print("   Linux: sudo apt install ffmpeg")
            print("   Mac: brew install ffmpeg")
            return [], None
        
        # Need both audio and video to sync
        if not audio_files:
            print("\n⚠ No audio files available. Skipping synchronization.")
            return [], None
        
        if not rendered_videos:
            print("\n⚠ No rendered videos available. Skipping synchronization.")
            return [], None
        
        # Get script segments for text content
        segments_path = file_manager.get_path('segments.json', 'script')
        script_segments = []
        
        if os.path.exists(segments_path):
            import json
            with open(segments_path, 'r', encoding='utf-8') as f:
                script_segments = json.load(f)
        
        # Create output folder for synced videos
        sync_output_folder = os.path.join(
            file_manager.session_folder,
            'final',
            'synced'
        )
        os.makedirs(sync_output_folder, exist_ok=True)
        
        # Synchronize all segments (each video adjusted to match audio duration)
        synced_segments = self.video_synchronizer.synchronize_segments(
            audio_files=audio_files,
            video_files=rendered_videos,
            script_segments=script_segments,
            output_folder=sync_output_folder,
            file_manager=file_manager
        )
        
        # Concatenate into final video
        final_video = None
        if synced_segments:
            # Inject Intro and Outro
            final_segments_list = list(synced_segments)
            
            # Intro
            intro_path = os.path.abspath(os.path.join('assets', 'branding', 'intro', 'Intro.mp4'))
            if os.path.exists(intro_path):
                print(f"  + Prepending Intro: {intro_path}")
                final_segments_list.insert(0, {'output_file': intro_path, 'duration': 3.0}) # approximate duration
            
            # Outro
            outro_path = os.path.abspath(os.path.join('assets', 'branding', 'outro', 'Outro.mp4'))
            if os.path.exists(outro_path):
                print(f"  + Appending Outro: {outro_path}")
                final_segments_list.append({'output_file': outro_path, 'duration': 8.0}) # approximate duration

            final_output_path = os.path.join(
                file_manager.session_folder,
                'final',
                'final_video.mp4'
            )
            
            final_video = self.video_synchronizer.concatenate_segments(
                synced_segments=final_segments_list,
                output_path=final_output_path
            )
        
        return synced_segments, final_video


    
    def _print_summary(self, metadata: dict):
        """Print processing summary"""
        print(f"\n{'='*60}")
        print("PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Session Folder: {metadata['session_folder']}")
        print(f"Processing Time: {metadata['processing_time_seconds']:.2f} seconds")

        
        # TTS Status
        if metadata.get('tts_available'):
            print(f"TTS Status: ✓ Available")
            print(f"Audio Files Generated: {metadata.get('audio_files_generated', 0)}")
        else:
            print(f"TTS Status: ✗ Not Available")
        
        # Video Rendering Status
        if metadata.get('video_rendering_available'):
            print(f"Manim Status: ✓ Available")
            print(f"Videos Rendered: {metadata.get('videos_rendered', 0)}")
        else:
            print(f"Manim Status: ✗ Not Available")
        
        # Synchronization Status
        if metadata.get('sync_available'):
            print(f"FFmpeg Status: ✓ Available")
            print(f"Segments Synchronized: {metadata.get('segments_synced', 0)}")
            if metadata.get('final_video'):
                print(f"Final Video: ✓ Created")
        else:
            print(f"FFmpeg Status: ✗ Not Available")
        
        print(f"\nGenerated Files:")
        for output_type, path in metadata['outputs'].items():
            if output_type == 'audio_files' and isinstance(path, list):
                if path:
                    print(f"  - {output_type}: {len(path)} files in audio/")
            elif output_type == 'rendered_videos' and isinstance(path, dict):
                if path:
                    print(f"  - {output_type}: {len(path)} videos in video/rendered/")
            elif output_type == 'synced_segments' and isinstance(path, list):
                if path:
                    print(f"  - {output_type}: {len(path)} videos in final/synced/")
            elif output_type == 'final_video' and path:
                print(f"  - {output_type}: {path}")
            elif output_type not in ['audio_files', 'rendered_videos', 'synced_segments']:
                print(f"  - {output_type}: {path}")
        
        print(f"\nNext Steps:")
        print(f"  1. Review the solution in: solver/")
        print(f"  2. Check audio script segments in: script/")
        
        # Dynamic next steps based on what's available
        step_num = 3
        
        if metadata.get('audio_files_generated', 0) > 0:
            print(f"  {step_num}. ✓ Audio files generated in: audio/ ({metadata['audio_files_generated']} files)")
            step_num += 1
        else:
            print(f"  {step_num}. Generate audio using TTS (neuTTS-air) - Install required")
            step_num += 1
        
        if metadata.get('videos_rendered', 0) > 0:
            print(f"  {step_num}. ✓ Videos rendered in: video/rendered/ ({metadata['videos_rendered']} scenes)")
            step_num += 1
        else:
            print(f"  {step_num}. Render Manim videos - Install Manim (pip install manim)")
            step_num += 1
        
        if metadata.get('segments_synced', 0) > 0:
            print(f"  {step_num}. ✓ Audio-video synchronized: final/synced/ ({metadata['segments_synced']} segments)")
            step_num += 1
        else:
            print(f"  {step_num}. Synchronize audio and video - Install FFmpeg")
            step_num += 1
        
        if metadata.get('final_video'):
            print(f"  {step_num}. ✓ FINAL VIDEO READY: {os.path.basename(metadata['final_video'])}")
            print(f"\n🎉 SUCCESS! Your complete educational video is ready!")
            print(f"📁 Location: {metadata['final_video']}")
        else:
            print(f"  {step_num}. Concatenate segments into final video")
        
        print(f"{'='*60}\n")
