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
            return False
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            print("⚠ Manim not found - video rendering will be skipped")
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
        Render a single Manim scene
        
        Args:
            script_path: Path to the Manim script
            scene_name: Name of the scene class to render
            quality: Quality flag (l=low, m=medium, h=high, k=4k)
            output_name: Optional custom output filename
        
        Returns:
            Path to rendered video file, or None if failed
        """
        try:
            # Build manim command
            quality_flag = f'-q{quality}'
            cmd = ['manim', quality_flag, script_path, scene_name]
            
            print(f"\n🎬 Rendering scene: {scene_name}")
            print(f"   Command: {' '.join(cmd)}")
            
            # Run manim
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                # Find the output video
                video_path = self._find_rendered_video(script_path, scene_name, quality)
                
                if video_path and os.path.exists(video_path):
                    print(f"✓ Rendered successfully: {video_path}")
                    
                    # Optionally rename
                    if output_name:
                        new_path = self._rename_video(video_path, output_name)
                        return new_path
                    
                    return video_path
                else:
                    print(f"⚠ Rendering completed but video not found")
                    return None
            else:
                print(f"❌ Rendering failed:")
                print(f"   Error: {result.stderr}")
                return None
        
        except subprocess.TimeoutExpired:
            print(f"❌ Rendering timed out after 10 minutes")
            return None
        except Exception as e:
            print(f"❌ Rendering error: {e}")
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
        
        # Render each scene
        for idx, scene_name in enumerate(scenes, 1):
            # Custom output name with index
            output_name = f"scene_{idx:02d}_{scene_name}"
            
            video_path = self.render_scene(
                script_path=script_path,
                scene_name=scene_name,
                quality=quality,
                output_name=None  # We'll copy later
            )
            
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
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"RENDERING SUMMARY")
        print(f"{'='*60}")
        print(f"Total scenes: {len(scenes)}")
        print(f"Successfully rendered: {len(rendered_videos)}")
        
        if rendered_videos:
            print(f"\nRendered videos:")
            for scene, path in rendered_videos.items():
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
        rendered_pairs = []
        
        # Match scenes to audio segments (1:1 or distribute)
        num_scenes = len(scenes)
        num_audio = len(audio_segments)
        
        print(f"\n📊 Alignment: {num_scenes} scenes, {num_audio} audio segments")
        
        for idx, scene_name in enumerate(scenes):
            # Determine which audio segment to pair
            if num_audio > 0:
                audio_idx = min(idx, num_audio - 1)  # Use last audio if scenes > audio
                audio_file = audio_segments[audio_idx]
            else:
                audio_file = None
            
            # Render scene
            video_path = self.render_scene(script_path, scene_name, quality)
            
            if video_path:
                final_video = self._copy_to_output_folder(
                    video_path,
                    output_folder,
                    f"scene_{idx+1:02d}_{scene_name}"
                )
                rendered_pairs.append((final_video, audio_file))
                
                if audio_file:
                    print(f"  📎 Paired with: {os.path.basename(audio_file)}")
        
        return rendered_pairs
