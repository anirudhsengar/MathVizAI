"""
TTS Generator module - converts text to speech using neuTTS-air
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional
import json

# Add neuTTS-air to path
NEUTTS_PATH = r'..\neutts-air'
if NEUTTS_PATH not in sys.path:
    sys.path.insert(0, NEUTTS_PATH)

try:
    from neuttsair.neutts import NeuTTSAir
    import soundfile as sf
    NEUTTS_AVAILABLE = True
except ImportError:
    NEUTTS_AVAILABLE = False
    print("Warning: neuTTS-air not available. TTS generation will be skipped.")

from utils.file_manager import FileManager
import config


class TTSGenerator:
    """Generates audio from text using neuTTS-air"""
    
    def __init__(self):
        """Initialize the TTS generator"""
        self.tts = None
        self.ref_codes = None
        self.reference_text = None
        
        if not NEUTTS_AVAILABLE:
            print("\n" + "="*60)
            print("⚠ neuTTS-air not available")
            print("TTS generation will be skipped")
            print("="*60)
            return
        
        # Initialize TTS model
        try:
            print("\n" + "="*60)
            print("Initializing neuTTS-air...")
            print("="*60)
            
            self.tts = NeuTTSAir(
                backbone_repo="neuphonic/neutts-air",
                backbone_device="cpu",
                codec_repo="neuphonic/neucodec",
                codec_device="cpu"
            )
            
            print("✓ neuTTS-air initialized successfully")
            
        except Exception as e:
            print(f"✗ Failed to initialize neuTTS-air: {str(e)}")
            self.tts = None
    
    def load_reference_voice(self, reference_audio_path: str, reference_text_path: str) -> bool:
        """
        Load and encode reference voice
        
        Args:
            reference_audio_path: Path to reference audio file (.wav)
            reference_text_path: Path to reference transcript text file
        
        Returns:
            True if successful, False otherwise
        """
        if not self.tts:
            print("⚠ TTS model not initialized")
            return False
        
        try:
            # Read reference text
            with open(reference_text_path, 'r', encoding='utf-8') as f:
                self.reference_text = f.read().strip()
            
            print(f"\nLoading reference voice from: {reference_audio_path}")
            print(f"Reference text: {self.reference_text[:100]}...")
            
            # Encode reference audio
            self.ref_codes = self.tts.encode_reference(reference_audio_path)
            
            print("✓ Reference voice loaded successfully")
            return True
            
        except Exception as e:
            print(f"✗ Failed to load reference voice: {str(e)}")
            return False
    
    def generate_audio_segments(
        self, 
        segments: List[Dict], 
        file_manager: FileManager,
        reference_audio: Optional[str] = None,
        reference_text: Optional[str] = None
    ) -> List[str]:
        """
        Generate audio for each segment
        
        Args:
            segments: List of segment dictionaries with 'number' and 'audio' keys
            file_manager: File manager instance
            reference_audio: Path to reference audio (optional, uses default if not provided)
            reference_text: Path to reference text (optional, uses default if not provided)
        
        Returns:
            List of paths to generated audio files
        """
        if not self.tts:
            print("\n" + "="*60)
            print("TTS GENERATOR - SKIPPED")
            print("="*60)
            print("⚠ neuTTS-air not available. Audio generation skipped.")
            return []
        
        print(f"\n{'='*60}")
        print(f"TTS GENERATOR")
        print(f"{'='*60}")
        
        # Load reference voice if provided
        if reference_audio and reference_text:
            if not self.load_reference_voice(reference_audio, reference_text):
                return []
        elif not self.ref_codes:
            # Try to load default reference
            default_audio = os.path.join("audio", config.DEFAULT_REFERENCE_AUDIO)
            default_text = os.path.join("audio", config.DEFAULT_REFERENCE_TEXT)
            
            if os.path.exists(default_audio) and os.path.exists(default_text):
                print(f"Using default reference voice: {default_audio}")
                if not self.load_reference_voice(default_audio, default_text):
                    return []
            else:
                print("✗ No reference voice available")
                print(f"Expected: {default_audio} and {default_text}")
                return []
        
        # Generate audio for each segment
        audio_files = []
        total_segments = len(segments)
        
        for idx, segment in enumerate(segments, 1):
            segment_num = segment.get('number', idx)
            text = segment.get('audio', '').strip()
            
            if not text:
                print(f"⚠ Segment {segment_num}: No text to generate")
                continue
            
            print(f"\n[{idx}/{total_segments}] Generating audio for segment {segment_num}...")
            print(f"Text preview: {text[:80]}...")
            
            try:
                # Generate speech
                wav = self.tts.infer(text, self.ref_codes, self.reference_text)
                
                # Save audio file
                filename = f"segment_{segment_num:02d}.wav"
                filepath = file_manager.get_path(filename, 'audio')
                
                sf.write(filepath, wav, 24000)
                audio_files.append(filepath)
                
                # Calculate duration
                duration = len(wav) / 24000
                print(f"✓ Saved: {filepath} (Duration: {duration:.1f}s)")
                
            except Exception as e:
                print(f"✗ Failed to generate segment {segment_num}: {str(e)}")
                continue
        
        print(f"\n{'='*60}")
        print(f"✓ Generated {len(audio_files)}/{total_segments} audio files")
        print(f"{'='*60}\n")
        
        # Save metadata about generated audio
        audio_metadata = {
            'total_segments': total_segments,
            'generated': len(audio_files),
            'reference_audio': reference_audio or config.DEFAULT_REFERENCE_AUDIO,
            'sample_rate': 24000,
            'files': [os.path.basename(f) for f in audio_files]
        }
        file_manager.save_json(audio_metadata, 'audio_metadata.json', 'audio')
        
        return audio_files
    
    def generate_single_audio(
        self,
        text: str,
        output_path: str,
        reference_audio: Optional[str] = None,
        reference_text_path: Optional[str] = None
    ) -> bool:
        """
        Generate audio for a single text
        
        Args:
            text: Text to convert to speech
            output_path: Path to save output audio
            reference_audio: Path to reference audio
            reference_text_path: Path to reference text
        
        Returns:
            True if successful, False otherwise
        """
        if not self.tts:
            print("⚠ TTS model not initialized")
            return False
        
        # Load reference if provided
        if reference_audio and reference_text_path:
            if not self.load_reference_voice(reference_audio, reference_text_path):
                return False
        
        if not self.ref_codes:
            print("✗ No reference voice loaded")
            return False
        
        try:
            print(f"Generating audio...")
            wav = self.tts.infer(text, self.ref_codes, self.reference_text)
            
            sf.write(output_path, wav, 24000)
            duration = len(wav) / 24000
            
            print(f"✓ Audio saved: {output_path} (Duration: {duration:.1f}s)")
            return True
            
        except Exception as e:
            print(f"✗ Failed to generate audio: {str(e)}")
            return False
    
    def is_available(self) -> bool:
        """Check if TTS is available and initialized"""
        return self.tts is not None
