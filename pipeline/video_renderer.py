"""
Video Renderer module - automates Manim video rendering
Handles multiple scenes, rendering management, and output organization
"""
import subprocess
import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import config
import concurrent.futures
import time


class VideoRenderer:
    """Automates Manim video rendering with scene detection and management"""
    
    def __init__(self):
        """Initialize the video renderer"""
        self.manim_available = self._check_manim()
    
    def _check_manim(self) -> bool:
        """
        Check if Manim is installed and available
        
        Returns:
            True if Manim is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['manim', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✓ Manim detected: {version}")
                return True
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            print("⚠ Manim not found - video rendering will be skipped")
            return False

    def check_latex_availability(self) -> bool:
        """Check if LaTeX is available and working by compiling a simple file"""
        try:
            # 1. Check if pdflatex exists
            result = subprocess.run(['pdflatex', '--version'], capture_output=True)
            if result.returncode != 0:
                print("⚠ LaTeX (pdflatex) not found")
                return False
                
            # 2. Try to compile a minimal LaTeX file to check for packages
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.tex', mode='w', delete=False) as f:
                # Use standalone class as Manim relies on it
                f.write(r"\documentclass{standalone}\usepackage{amsmath}\begin{document}Test\end{document}")
                tex_path = f.name
                
            cmd = ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', '-output-directory', os.path.dirname(tex_path), tex_path]
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            
            # Cleanup
            try:
                os.remove(tex_path)
                os.remove(tex_path.replace('.tex', '.log'))
                os.remove(tex_path.replace('.tex', '.aux'))
                os.remove(tex_path.replace('.tex', '.pdf'))
            except:
                pass

            if result.returncode == 0:
                print("✓ LaTeX detected and working (packages available)")
                return True
            else:
                print("⚠ LaTeX detected but compilation failed (missing packages?)")
                print("  Falling back to Text() to ensure stability.")
                return False
                
        except Exception as e:
            print(f"⚠ LaTeX check failed: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if renderer is available"""
        return self.manim_available
    
    def extract_scene_classes(self, script_path: str) -> List[str]:
        """
        Extract all Manim scene class names from a Python script
        
        Args:
            script_path: Path to the Manim Python script
        
        Returns:
            List of scene class names
        """
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Pattern to match: class SceneName(Scene):
            pattern = r'class\s+(\w+)\s*\(\s*Scene\s*\)\s*:'
            matches = re.findall(pattern, content)
            
            if matches:
                print(f"✓ Found {len(matches)} scene(s): {', '.join(matches)}")
                return matches
            else:
                print("⚠ No Scene classes found in script")
                return []
        
        except Exception as e:
            print(f"❌ Error extracting scenes: {e}")
            return []
    
    def render_scene(
        self,
        script_path: str,
        scene_name: str,
        quality: str = 'h',
        output_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Render a single Manim scene as PNG sequence and stitch to video
        
        Args:
            script_path: Path to the Manim script
            scene_name: Name of the scene class to render
            quality: Quality flag (l=low, m=medium, h=high, k=4k)
            output_name: Optional custom output filename
        
        Returns:
            Path to rendered video file, or None if failed
        """
        try:
            # 1. Render as PNG sequence (bypassing av library issues)
            # -r is for resolution (not needed if quality is set), --format=png is key
            quality_flag = f'-q{quality}'
            cmd = ['manim', quality_flag, '--format=png', script_path, scene_name]
            
            print(f"\n🎬 Rendering scene as PNG sequence: {scene_name}")
            print(f"   Command: {' '.join(cmd)}")
            
            # Retry logic for rendering
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=config.MANIM_TIMEOUT  # Use configured timeout
                    )
                    
                    if result.returncode == 0:
                        break
                        
                    # If failed, check if it's a DVI error (transient)
                    if "can't open file" in result.stderr and ".dvi" in result.stderr:
                        print(f"⚠ DVI/SVG conversion error (attempt {attempt+1}/{max_retries}). Retrying...")
                        time.sleep(2) # Wait a bit before retry
                        continue
                        
                    # Other errors - break immediately unless we implement specific handling
                    # For now, let's just print and retry for any error just in case it's transient
                    print(f"⚠ Rendering failed (attempt {attempt+1}/{max_retries}). Retrying...")
                    
                except subprocess.TimeoutExpired:
                    if attempt == max_retries - 1:
                        print(f"❌ Rendering timed out after {config.MANIM_TIMEOUT}s")
                        return None
                    print(f"⚠ Rendering timed out (attempt {attempt+1}/{max_retries}). Retrying...")
            
            if result.returncode != 0:
                print(f"❌ Rendering process failed.")
                print(f"   Error: {result.stderr}")
                return None
                
            print(f"✓ PNG Rendering completed. Stitching video...")
            
            # 2. Stitch PNGs to Video using FFmpeg
            video_path = self._stitch_pngs_to_video(script_path, scene_name, quality)
            
            if video_path and os.path.exists(video_path):
                print(f"✓ Video successfully generated: {video_path}")
                
                # Optionally rename
                if output_name:
                    new_path = self._rename_video(video_path, output_name)
                    return new_path
                
                return video_path
            else:
                print(f"❌ Failed to generate video from images")
                return None
        
        except subprocess.TimeoutExpired:
            print(f"❌ Rendering timed out after 20 minutes")
            return None
        except Exception as e:
            print(f"❌ Rendering error: {e}")
            return None

    def _stitch_pngs_to_video(self, script_path: str, scene_name: str, quality: str) -> Optional[str]:
        """
        Stitch rendered PNG sequence into an MP4 video
        """
        try:
            script_dir = os.path.dirname(os.path.abspath(script_path))
            script_name = os.path.splitext(os.path.basename(script_path))[0]
            
            # Locate images
            # Manim stores images in media/images/{script_name}/{image_prefix}*.png
            # For a scene named 'ProveSqrt2Irrational', images are ProveSqrt2Irrational0000.png, etc.
            # located in media/images/{script_name}/
            
            image_dir = os.path.join(script_dir, 'media', 'images', script_name)
            
            if not os.path.exists(image_dir):
                # Try project root media
                project_root = os.getcwd()
                image_dir = os.path.join(project_root, 'media', 'images', script_name)
            
            if not os.path.exists(image_dir):
                print(f"❌ Image directory not found: {image_dir}")
                return None

            # Pattern for ffmpeg
            # %04d matches 0000, 0001, etc.
            image_pattern = os.path.join(image_dir, f"{scene_name}%04d.png")
            
            # Determine framerate based on quality
            fps_map = {'l': 15, 'm': 30, 'h': 60, 'k': 60}
            fps = fps_map.get(quality, 60)
            
            # Output file path (place it where Manim usually puts videos for consistency)
            quality_dirs = {'l': '480p15', 'm': '720p30', 'h': '1080p60', 'k': '2160p60'}
            quality_dir = quality_dirs.get(quality, '1080p60')
            
            output_dir = os.path.join(script_dir, 'media', 'videos', script_name, quality_dir)
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{scene_name}.mp4")
            
            cmd = [
                'ffmpeg',
                '-y', # Overwrite
                '-framerate', str(fps),
                '-i', image_pattern,
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p', # Ensure compatibility
                output_file
            ]
            
            # print(f"   Stitching command: {' '.join(cmd)}")
            subprocess.run(cmd, capture_output=True, check=True)
            
            if os.path.exists(output_file):
                return output_file
            return None
            
        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg stitching failed: {e}")
            return None
        except Exception as e:
            print(f"❌ Error stitching video: {e}")
            return None
    
    def _find_rendered_video(self, script_path: str, scene_name: str, quality: str) -> Optional[str]:
        """
        Find the rendered video file in Manim's output structure
        
        Args:
            script_path: Path to the Manim script
            scene_name: Scene class name
            quality: Quality flag used
        
        Returns:
            Path to video file if found
        """
        # Manim output structure: media/videos/{script_name}/{quality}/
        script_dir = os.path.dirname(os.path.abspath(script_path))
        script_name = os.path.splitext(os.path.basename(script_path))[0]
        
        # Quality directory mapping
        quality_dirs = {
            'l': '480p15',
            'm': '720p30',
            'h': '1080p60',
            'k': '2160p60'
        }
        quality_dir = quality_dirs.get(quality, '1080p60')
        
        # Possible video locations
        possible_paths = [
            # Default Manim output
            os.path.join(script_dir, 'media', 'videos', script_name, quality_dir, f'{scene_name}.mp4'),
            # Alternative location
            os.path.join('media', 'videos', script_name, quality_dir, f'{scene_name}.mp4'),
            # Current directory
            os.path.join(script_dir, f'{scene_name}.mp4'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Search recursively in media folder
        media_dir = os.path.join(script_dir, 'media')
        if os.path.exists(media_dir):
            for root, dirs, files in os.walk(media_dir):
                for file in files:
                    if file == f'{scene_name}.mp4':
                        return os.path.join(root, file)
        
        return None
    
    def _rename_video(self, video_path: str, new_name: str) -> str:
        """
        Rename a video file
        
        Args:
            video_path: Current video path
            new_name: New filename (without extension)
        
        Returns:
            New video path
        """
        try:
            directory = os.path.dirname(video_path)
            new_path = os.path.join(directory, f'{new_name}.mp4')
            shutil.move(video_path, new_path)
            print(f"✓ Renamed to: {new_name}.mp4")
            return new_path
        except Exception as e:
            print(f"⚠ Could not rename video: {e}")
            return video_path
    
    def render_all_scenes(
        self,
        script_path: str,
        output_folder: str,
        quality: str = 'h'
    ) -> Dict[str, str]:
        """
        Render all scenes from a Manim script
        
        Args:
            script_path: Path to the Manim script
            output_folder: Folder to organize final videos
            quality: Quality flag
        
        Returns:
            Dictionary mapping scene names to video paths
        """
        print(f"\n{'='*60}")
        print(f"VIDEO RENDERING")
        print(f"{'='*60}")
        
        if not self.is_available():
            print("⚠ Manim not available - skipping rendering")
            return {}
        
        # Extract scenes
        scenes = self.extract_scene_classes(script_path)
        if not scenes:
            print("⚠ No scenes to render")
            return {}
        
        rendered_videos = {}
        
        # Render scenes in parallel
        max_workers = getattr(config, 'MAX_RENDER_WORKERS', 4)
        print(f"   Starting parallel rendering (workers={max_workers})...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_scene = {}
            
            for idx, scene_name in enumerate(scenes, 1):
                # Custom output name with index
                output_name = f"scene_{idx:02d}_{scene_name}"
                
                # Submit task
                future = executor.submit(
                    self.render_scene,
                    script_path,
                    scene_name,
                    quality,
                    None # Output name handled later to avoid confusion
                )
                future_to_scene[future] = (scene_name, output_name)
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_scene):
                scene_name, output_name = future_to_scene[future]
                try:
                    video_path = future.result()
                    if video_path:
                        # Copy to output folder
                        final_path = self._copy_to_output_folder(
                            video_path,
                            output_folder,
                            output_name
                        )
                        rendered_videos[scene_name] = final_path
                    else:
                        print(f"⚠ Failed to render: {scene_name}")
                except Exception as exc:
                    print(f"❌ {scene_name} generated an exception: {exc}")

        # Print summary
        print(f"\n{'='*60}")
        print(f"RENDERING SUMMARY")
        print(f"{'='*60}")
        print(f"Total scenes: {len(scenes)}")
        print(f"Successfully rendered: {len(rendered_videos)}")
        
        if rendered_videos:
            print(f"\nRendered videos:")
            # Sort by scene index for better readability
            sorted_scenes = sorted(rendered_videos.items(), key=lambda x: x[1])
            for scene, path in sorted_scenes:
                print(f"  • {scene}: {path}")
        
        return rendered_videos
    
    def _copy_to_output_folder(self, video_path: str, output_folder: str, name: str) -> str:
        """
        Copy video to organized output folder
        
        Args:
            video_path: Source video path
            output_folder: Destination folder
            name: Output filename (without extension)
        
        Returns:
            Final video path
        """
        try:
            os.makedirs(output_folder, exist_ok=True)
            final_path = os.path.join(output_folder, f'{name}.mp4')
            shutil.copy2(video_path, final_path)
            print(f"✓ Copied to: {final_path}")
            return final_path
        except Exception as e:
            print(f"⚠ Could not copy video: {e}")
            return video_path
    
    def render_with_audio_alignment(
        self,
        script_path: str,
        audio_segments: List[str],
        output_folder: str,
        quality: str = 'h'
    ) -> List[Tuple[str, Optional[str]]]:
        """
        Render scenes with audio alignment hints
        
        Args:
            script_path: Path to Manim script
            audio_segments: List of audio file paths
            output_folder: Output folder for videos
            quality: Quality flag
        
        Returns:
            List of tuples (video_path, audio_path) for each scene
        """
        scenes = self.extract_scene_classes(script_path)
        
        # Multi-scene rendering - one video per scene

        rendered_pairs = [] # Store as (index, (video_path, audio_path)) to sort later
        
        # Match scenes to audio segments (1:1 or distribute)
        num_scenes = len(scenes)
        num_audio = len(audio_segments)
        
        print(f"\n📊 Alignment: {num_scenes} scenes, {num_audio} audio segments")
        
        # Parallel execution
        max_workers = getattr(config, 'MAX_RENDER_WORKERS', 4)
        print(f"   Starting parallel rendering with audio alignment (workers={max_workers})...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {}
            
            for idx, scene_name in enumerate(scenes):
                # Determine which audio segment to pair
                if num_audio > 0:
                    audio_idx = min(idx, num_audio - 1)
                    audio_file = audio_segments[audio_idx]
                else:
                    audio_file = None
                
                # Submit task
                future = executor.submit(
                    self.render_scene,
                    script_path,
                    scene_name,
                    quality
                )
                future_to_idx[future] = (idx, scene_name, audio_file)
            
            # Process results
            results = []
            for future in concurrent.futures.as_completed(future_to_idx):
                idx, scene_name, audio_file = future_to_idx[future]
                try:
                    video_path = future.result()
                    if video_path:
                        final_video = self._copy_to_output_folder(
                            video_path,
                            output_folder,
                            f"scene_{idx+1:02d}_{scene_name}"
                        )
                        results.append((idx, (final_video, audio_file)))
                        
                        if audio_file:
                            print(f"  ✓ {scene_name}: Paired with {os.path.basename(audio_file)}")
                    else:
                        print(f"  ❌ {scene_name}: Failed to render")
                except Exception as exc:
                    print(f"  ❌ {scene_name} generated an exception: {exc}")
        
        # Sort results by index to maintain valid order
        results.sort(key=lambda x: x[0])
        rendered_pairs = [x[1] for x in results]
        
        return rendered_pairs

    def _render_sections(
        self,
        script_path: str,
        scene_name: str,
        audio_segments: List[str],
        output_folder: str,
        quality: str
    ) -> List[Tuple[str, Optional[str]]]:
        """
        Render a single scene as PNG sequence and stitch to video.
        This approach bypasses the av library corruption issues.
        """
        try:
            # 1. Run Manim with --format=png (bypasses av library video corruption)
            quality_flag = f'-q{quality}'
            script_dir = os.path.dirname(script_path)
            cmd = ['manim', quality_flag, '--format=png', '--media_dir', script_dir, script_path, scene_name]
            
            print(f"   Executing (PNG mode): {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.MANIM_TIMEOUT
            )
            
            if result.returncode != 0:
                print(f"⚠ Manim PNG rendering failed.")
                print(f"   stderr: {result.stderr[:500] if result.stderr else 'No error output'}")
                return []
            
            print(f"✓ PNG rendering completed. Stitching video...")
            
            # 2. Find PNG sequence
            script_name = os.path.splitext(os.path.basename(script_path))[0]
            quality_dirs = {'l': '480p15', 'm': '720p30', 'h': '1080p60', 'k': '2160p60'}
            quality_dir = quality_dirs.get(quality, '1080p60')
            
            # Possible image locations with --media_dir
            possible_image_paths = [
                os.path.join(script_dir, 'images', script_name),         # --media_dir style
                os.path.join(script_dir, 'media', 'images', script_name), # default style
            ]
            
            image_dir = None
            for path in possible_image_paths:
                if os.path.exists(path):
                    # Check if there are PNG files
                    pngs = [f for f in os.listdir(path) if f.endswith('.png') and f.startswith(scene_name)]
                    if pngs:
                        image_dir = path
                        print(f"✓ Found {len(pngs)} PNG files in: {path}")
                        break
            
            if not image_dir:
                print(f"❌ No PNG files found for scene {scene_name}")
                return []
            
            # 3. Stitch PNGs to video using FFmpeg
            fps_map = {'l': 15, 'm': 30, 'h': 60, 'k': 60}
            fps = fps_map.get(quality, 60)
            
            # Pattern for ffmpeg input (Manim names images as SceneName0000.png, SceneName0001.png, etc.)
            image_pattern = os.path.join(image_dir, f"{scene_name}%04d.png")
            
            # Ensure output folder exists
            os.makedirs(output_folder, exist_ok=True)
            
            # Output video path
            full_video_path = os.path.join(output_folder, 'full_scene.mp4')
            
            stitch_cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-framerate', str(fps),
                '-i', image_pattern,
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',  # Ensure compatibility
                '-preset', 'medium',
                full_video_path
            ]
            
            print(f"   Stitching {len([f for f in os.listdir(image_dir) if f.endswith('.png')])} frames...")
            print(f"   Output path: {full_video_path}")
            stitch_result = subprocess.run(stitch_cmd, capture_output=True, text=True, timeout=300)
            
            if stitch_result.returncode != 0:
                print(f"❌ FFmpeg failed (exit {stitch_result.returncode})")
                print(f"   stderr: {stitch_result.stderr[-1000:] if stitch_result.stderr else 'No error output'}")
            
            if os.path.exists(full_video_path) and os.path.getsize(full_video_path) > 0:
                print(f"✓ Stitched full video: {full_video_path}")
                # Return special signal for Orchestrator
                return [('FULL_VIDEO_MODE', full_video_path)]
            else:
                print(f"❌ FFmpeg stitch failed: {stitch_result.stderr[:500] if stitch_result.stderr else 'Unknown error'}")
                return []
            
        except subprocess.TimeoutExpired:
            print(f"❌ Rendering timed out")
            return []
        except Exception as e:
            print(f"❌ Section rendering error: {e}")
            return []


    def verify_scene_code(self, scene_code: str, scene_classname: str) -> Tuple[bool, str]:
        """
        Verifies if the generated scene code is renderable by running a dry run.
        
        Args:
            scene_code: The full Python code for the scene (including imports)
            scene_classname: The name of the scene class to test
            
        Returns:
            Tuple (success: bool, error_log: str)
        """
        import tempfile
        import shutil
        
        # Create a temp directory for this check
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, "test_verification.py")
            
            # Write the code
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(scene_code)
            
            # Construct check command
            # Using -ql (low quality) and -s (save last frame) to be as fast as possible
            # while still executing the code. --dry_run might skip too much logic.
            cmd = [
                "manim",
                "-ql",          # Low quality
                "-s",           # Save last frame only (faster than full video)
                "--disable_caching", # Ensure we actually run it
                script_path,
                scene_classname
            ]
            
            print(f"    Verifying {scene_classname}...")
            
            try:
                # Run with timeout to prevent hanging
                # Capture both stdout and stderr (Manim writes to both sometimes)
                env = os.environ.copy()
                env["COLUMNS"] = "200" # Force wider output to avoid wrapping
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=60, # 1 min timeout for verification
                    cwd=temp_dir, # Run in temp dir to contain outputs
                    env=env
                )
                
                if result.returncode == 0:
                    return True, ""
                else:
                    # Combine stdout and stderr for full context
                    # Manim often puts the critical "Exception: ..." in stdout or stderr depending on version
                    combined_log = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                    
                    # Return the last 3000 chars which likely contains the traceback
                    return False, f"Manim Verification Error:\n{combined_log[-3000:]}"
                    
            except subprocess.TimeoutExpired:
                return False, "Verification timed out after 60s."
            except Exception as e:
                return False, f"Verification failed to run: {str(e)}"
