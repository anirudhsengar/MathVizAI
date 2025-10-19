"""
Video Synchronizer module - aligns audio and video segments
Ensures audio duration matches video duration, generates text slides for missing videos
"""
import subprocess
import os
import json
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import config


class VideoSynchronizer:
    """Synchronizes audio and video segments with duration matching"""
    
    def __init__(self):
        """Initialize the video synchronizer"""
        self.ffmpeg_available = self._check_ffmpeg()
        self.ffprobe_available = self._check_ffprobe()
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is installed"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"✓ FFmpeg detected")
                return True
            return False
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            print("⚠ FFmpeg not found - video sync will be skipped")
            return False
    
    def _check_ffprobe(self) -> bool:
        """Check if FFprobe is installed (comes with FFmpeg)"""
        try:
            result = subprocess.run(
                ['ffprobe', '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def is_available(self) -> bool:
        """Check if synchronizer is available"""
        return self.ffmpeg_available and self.ffprobe_available
    
    def get_duration(self, file_path: str) -> Optional[float]:
        """
        Get duration of a media file in seconds
        
        Args:
            file_path: Path to media file (audio or video)
        
        Returns:
            Duration in seconds, or None if failed
        """
        if not self.ffprobe_available or not os.path.exists(file_path):
            return None
        
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            return None
        
        except Exception as e:
            print(f"⚠ Could not get duration for {file_path}: {e}")
            return None
    
    def generate_text_slide(
        self,
        text: str,
        duration: float,
        output_path: str,
        index: int
    ) -> Optional[str]:
        """
        Generate a Manim text slide video for audio without corresponding video
        
        Args:
            text: Text content to display
            duration: Duration in seconds
            output_path: Output video path
            index: Segment index for naming
        
        Returns:
            Path to generated video, or None if failed
        """
        try:
            # Create a temporary Manim script for text slide
            script_content = f'''
from manim import *

class TextSlide{index}(Scene):
    def construct(self):
        # Create text with word wrapping
        text_content = """{text}"""
        
        # Split into manageable lines
        max_width = 50
        words = text_content.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            if len(' '.join(current_line)) > max_width:
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(' '.join(current_line))
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Create text object
        text_obj = Text(
            '\\n'.join(lines),
            font_size=36,
            color=WHITE,
            line_spacing=1.2
        ).scale(0.8)
        
        # Add to scene with fade in/out
        self.play(FadeIn(text_obj), run_time=1)
        self.wait({duration - 2})  # Hold for most of the duration
        self.play(FadeOut(text_obj), run_time=1)
'''
            
            # Save script to temp location
            script_dir = os.path.dirname(output_path)
            temp_script = os.path.join(script_dir, f'temp_text_slide_{index}.py')
            
            with open(temp_script, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Render with Manim
            print(f"  📝 Generating text slide for segment {index}...")
            
            cmd = [
                'manim',
                '-qh',  # High quality
                '--format', 'mp4',
                '--media_dir', script_dir,
                temp_script,
                f'TextSlide{index}'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for text slides
            )
            
            if result.returncode == 0:
                # Find the generated video
                generated_video = self._find_text_slide_video(script_dir, f'TextSlide{index}')
                
                if generated_video and os.path.exists(generated_video):
                    # Move to desired location
                    os.replace(generated_video, output_path)
                    print(f"  ✓ Text slide generated: {os.path.basename(output_path)}")
                    
                    # Clean up temp script
                    try:
                        os.remove(temp_script)
                    except:
                        pass
                    
                    return output_path
            
            print(f"  ⚠ Failed to generate text slide")
            return None
        
        except Exception as e:
            print(f"  ❌ Error generating text slide: {e}")
            return None
    
    def _find_text_slide_video(self, base_dir: str, scene_name: str) -> Optional[str]:
        """Find generated text slide video in Manim output structure"""
        # Search for the video in media folder
        media_dir = os.path.join(base_dir, 'media')
        if os.path.exists(media_dir):
            for root, dirs, files in os.walk(media_dir):
                for file in files:
                    if file.startswith(scene_name) and file.endswith('.mp4'):
                        return os.path.join(root, file)
        return None
    
    def adjust_video_duration(
        self,
        video_path: str,
        target_duration: float,
        output_path: str
    ) -> Optional[str]:
        """
        Adjust video duration to match audio using speed adjustment or looping
        
        Args:
            video_path: Source video path
            target_duration: Target duration in seconds
            output_path: Output video path
        
        Returns:
            Path to adjusted video, or None if failed
        """
        try:
            current_duration = self.get_duration(video_path)
            if not current_duration:
                return None
            
            # If durations are close (within 0.5s), use as is
            if abs(current_duration - target_duration) < 0.5:
                return video_path
            
            print(f"  ⚙ Adjusting video duration: {current_duration:.2f}s → {target_duration:.2f}s")
            
            # Calculate speed adjustment factor
            speed_factor = current_duration / target_duration
            
            # If speed adjustment is reasonable (0.8x to 1.2x), use setpts
            if 0.8 <= speed_factor <= 1.2:
                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-filter:v', f'setpts={speed_factor}*PTS',
                    '-an',  # Remove audio from video
                    '-y',   # Overwrite output
                    output_path
                ]
            else:
                # For larger differences, trim or loop
                if current_duration > target_duration:
                    # Trim video
                    cmd = [
                        'ffmpeg',
                        '-i', video_path,
                        '-t', str(target_duration),
                        '-c', 'copy',
                        '-y',
                        output_path
                    ]
                else:
                    # Loop video to reach target duration
                    loops = int(target_duration / current_duration) + 1
                    cmd = [
                        'ffmpeg',
                        '-stream_loop', str(loops),
                        '-i', video_path,
                        '-t', str(target_duration),
                        '-c', 'copy',
                        '-y',
                        output_path
                    ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"  ✓ Duration adjusted successfully")
                return output_path
            else:
                print(f"  ⚠ Duration adjustment failed: {result.stderr}")
                return video_path  # Return original if adjustment fails
        
        except Exception as e:
            print(f"  ❌ Error adjusting duration: {e}")
            return video_path
    
    def merge_audio_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str
    ) -> Optional[str]:
        """
        Merge audio and video into a single file
        
        Args:
            video_path: Path to video file
            audio_path: Path to audio file
            output_path: Output path for merged file
        
        Returns:
            Path to merged file, or None if failed
        """
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',        # Copy video codec
                '-c:a', 'aac',         # Convert audio to AAC
                '-b:a', '192k',        # Audio bitrate
                '-shortest',           # End at shortest stream
                '-y',                  # Overwrite output
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                return output_path
            else:
                print(f"  ⚠ Merge failed: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"  ❌ Error merging audio/video: {e}")
            return None
    
    def synchronize_segments(
        self,
        audio_files: List[str],
        video_files: Dict[str, str],
        script_segments: List[Dict],
        output_folder: str,
        file_manager
    ) -> List[Dict[str, str]]:
        """
        Synchronize audio and video segments with duration matching
        
        Args:
            audio_files: List of audio file paths
            video_files: Dictionary mapping scene names to video paths
            script_segments: List of script segment data with text content
            output_folder: Output folder for synchronized videos
            file_manager: File manager instance
        
        Returns:
            List of dictionaries with sync info for each segment
        """
        print(f"\n{'='*60}")
        print(f"VIDEO SYNCHRONIZATION")
        print(f"{'='*60}")
        
        if not self.is_available():
            print("⚠ FFmpeg not available - skipping synchronization")
            print("   Install FFmpeg to enable audio-video sync:")
            print("   Windows: choco install ffmpeg")
            print("   Linux: sudo apt install ffmpeg")
            print("   Mac: brew install ffmpeg")
            return []
        
        os.makedirs(output_folder, exist_ok=True)
        
        # Convert video_files dict to list
        video_list = list(video_files.values()) if video_files else []
        
        num_audio = len(audio_files)
        num_video = len(video_list)
        
        print(f"\n📊 Segments to sync:")
        print(f"   Audio segments: {num_audio}")
        print(f"   Video segments: {num_video}")
        print(f"   Script segments: {len(script_segments)}")
        
        synced_segments = []
        
        # Process each audio segment
        for idx, audio_path in enumerate(audio_files, 1):
            print(f"\n🎬 Processing segment {idx}/{num_audio}...")
            
            # Get audio duration
            audio_duration = self.get_duration(audio_path)
            if not audio_duration:
                print(f"  ⚠ Could not get audio duration, skipping")
                continue
            
            print(f"  🔊 Audio duration: {audio_duration:.2f}s")
            
            # Determine video for this segment
            if idx <= num_video:
                # Use corresponding video
                video_path = video_list[idx - 1]
                video_duration = self.get_duration(video_path)
                
                print(f"  🎥 Using video: {os.path.basename(video_path)}")
                print(f"  📏 Video duration: {video_duration:.2f}s" if video_duration else "  ⚠ Could not get video duration")
                
                # Adjust video duration to match audio
                adjusted_video_path = os.path.join(
                    output_folder,
                    f'adjusted_{idx:02d}.mp4'
                )
                
                adjusted_video = self.adjust_video_duration(
                    video_path,
                    audio_duration,
                    adjusted_video_path
                )
                
                if not adjusted_video:
                    print(f"  ⚠ Using original video without adjustment")
                    adjusted_video = video_path
            
            else:
                # Generate text slide for missing video
                print(f"  📝 No video available - generating text slide")
                
                # Get text content from script segments
                text_content = ""
                if idx <= len(script_segments):
                    text_content = script_segments[idx - 1].get('text', f'Segment {idx}')
                else:
                    text_content = f'Segment {idx}'
                
                adjusted_video_path = os.path.join(
                    output_folder,
                    f'text_slide_{idx:02d}.mp4'
                )
                
                adjusted_video = self.generate_text_slide(
                    text=text_content,
                    duration=audio_duration,
                    output_path=adjusted_video_path,
                    index=idx
                )
                
                if not adjusted_video:
                    print(f"  ⚠ Could not generate text slide, skipping segment")
                    continue
            
            # Merge audio and adjusted video
            print(f"  🔄 Merging audio and video...")
            
            output_path = os.path.join(
                output_folder,
                f'synced_{idx:02d}.mp4'
            )
            
            merged = self.merge_audio_video(
                video_path=adjusted_video,
                audio_path=audio_path,
                output_path=output_path
            )
            
            if merged:
                print(f"  ✓ Synced: {os.path.basename(output_path)}")
                
                synced_segments.append({
                    'index': idx,
                    'audio_file': audio_path,
                    'video_file': video_list[idx - 1] if idx <= num_video else 'text_slide',
                    'output_file': output_path,
                    'duration': audio_duration
                })
            else:
                print(f"  ❌ Failed to merge segment {idx}")
        
        # Save sync metadata
        if synced_segments:
            sync_metadata = {
                'total_segments': len(synced_segments),
                'total_duration': sum(s['duration'] for s in synced_segments),
                'segments': synced_segments
            }
            file_manager.save_metadata(sync_metadata, 'sync_metadata.json', 'final')
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"SYNCHRONIZATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total segments synchronized: {len(synced_segments)}")
        
        if synced_segments:
            total_duration = sum(s['duration'] for s in synced_segments)
            print(f"Total duration: {total_duration:.2f}s ({total_duration/60:.1f} minutes)")
            print(f"\nSynchronized videos:")
            for segment in synced_segments:
                print(f"  • Segment {segment['index']}: {os.path.basename(segment['output_file'])} ({segment['duration']:.2f}s)")
        
        return synced_segments
    
    def concatenate_segments(
        self,
        synced_segments: List[Dict[str, str]],
        output_path: str
    ) -> Optional[str]:
        """
        Concatenate all synced segments into a single final video
        
        Args:
            synced_segments: List of synced segment info
            output_path: Output path for final video
        
        Returns:
            Path to final video, or None if failed
        """
        if not synced_segments:
            print("⚠ No segments to concatenate")
            return None
        
        print(f"\n{'='*60}")
        print(f"CONCATENATING FINAL VIDEO")
        print(f"{'='*60}")
        
        try:
            # Create concat file list
            concat_file = os.path.join(
                os.path.dirname(output_path),
                'concat_list.txt'
            )
            
            with open(concat_file, 'w', encoding='utf-8') as f:
                for segment in synced_segments:
                    # FFmpeg requires forward slashes even on Windows
                    video_path = segment['output_file'].replace('\\', '/')
                    f.write(f"file '{video_path}'\n")
            
            print(f"📋 Concatenating {len(synced_segments)} segments...")
            
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                '-y',
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                print(f"✓ Final video created: {os.path.basename(output_path)}")
                print(f"  Size: {file_size:.2f} MB")
                print(f"  Path: {output_path}")
                
                # Clean up concat file
                try:
                    os.remove(concat_file)
                except:
                    pass
                
                return output_path
            else:
                print(f"❌ Concatenation failed: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"❌ Error concatenating videos: {e}")
            return None
