"""
TTS Generator module - converts text to speech using Microsoft VibeVoice
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional
import json
import torch
import soundfile as sf
import copy

try:
    from vibevoice.modular import VibeVoiceStreamingForConditionalGenerationInference
    from vibevoice.processor import VibeVoiceStreamingProcessor
    VIBEVOICE_AVAILABLE = True
except ImportError:
    VIBEVOICE_AVAILABLE = False
    print("Warning: VibeVoice not available. TTS generation will be skipped.")

from utils.file_manager import FileManager
import config


class TTSGenerator:
    """Generates audio from text using Microsoft VibeVoice"""
    
    def __init__(self):
        """Initialize the TTS generator"""
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.bfloat16 if self.device == "cuda" else torch.float32

        if not VIBEVOICE_AVAILABLE:
            print("\n" + "="*60)
            print("⚠ VibeVoice not available")
            print("TTS generation will be skipped")
            print("="*60)
            return
        
        # Initialize TTS model
        try:
            print("\n" + "="*60)
            print("Initializing VibeVoice...")
            print(f"Device: {self.device}")
            print("="*60)
            
            self.processor = VibeVoiceStreamingProcessor.from_pretrained(config.VIBE_VOICE_MODEL)
            self.model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                config.VIBE_VOICE_MODEL,
                torch_dtype=self.torch_dtype,
                device_map=self.device,
            )
            
            print("✓ VibeVoice initialized successfully")
            
        except Exception as e:
            print(f"✗ Failed to initialize VibeVoice: {str(e)}")
            self.model = None
            self.processor = None
    
    def generate_audio_segments(
        self, 
        segments: List[Dict], 
        file_manager: FileManager,
        reference_audio: Optional[str] = None, # Unused in VibeVoice base usage for now
        reference_text: Optional[str] = None   # Unused
    ) -> List[str]:
        """
        Generate audio for each segment
        
        Args:
            segments: List of segment dictionaries with 'number' and 'audio' keys
            file_manager: File manager instance
            reference_audio: Path to reference audio (optional)
            reference_text: Path to reference text (optional)
        
        Returns:
            List of paths to generated audio files
        """
        if not self.model or not self.processor:
            print("\n" + "="*60)
            print("TTS GENERATOR - SKIPPED")
            print("="*60)
            print("⚠ VibeVoice not available. Audio generation skipped.")
            return []
        
        print(f"\n{'='*60}")
        print(f"TTS GENERATOR (VibeVoice)")
        print(f"{'='*60}")
        
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
                # Load prompt if not already loaded (cache it if needed)
                # Ideally this should be done in __init__ but we need to match device
                if not hasattr(self, 'cached_prompt'):
                     if os.path.exists(config.VIBE_VOICE_PRESET_PATH):
                        print(f"Loading voice preset from {config.VIBE_VOICE_PRESET_PATH}")
                        self.cached_prompt = torch.load(config.VIBE_VOICE_PRESET_PATH, map_location=self.device, weights_only=False)
                     else:
                        print(f"⚠ Voice preset not found at {config.VIBE_VOICE_PRESET_PATH}")
                        # Fallback or error?
                        self.cached_prompt = None

                if self.cached_prompt is None:
                     print("✗ No voice preset loaded, cannot generate audio")
                     continue

                # Prepare inputs
                inputs = self.processor.process_input_with_cached_prompt(
                    text=text,
                    cached_prompt=self.cached_prompt,
                    padding=True,
                    return_tensors="pt",
                    return_attention_mask=True,
                )
                
                # Move tensors to device
                for k, v in inputs.items():
                    if torch.is_tensor(v):
                        inputs[k] = v.to(self.device)

                # Generate speech
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=None,
                        cfg_scale=1.5,
                        tokenizer=self.processor.tokenizer,
                        generation_config={'do_sample': False},
                        all_prefilled_outputs=copy.deepcopy(self.cached_prompt) if self.cached_prompt is not None else None
                    )
                
                if outputs.speech_outputs and outputs.speech_outputs[0] is not None:
                    wav = outputs.speech_outputs[0]
                    
                    # Save audio file
                    filename = f"segment_{segment_num:02d}.wav"
                    filepath = file_manager.get_path(filename, 'audio')
                    
                    # VibeVoice creates 24kHz audio, shape (channels, time) usually (1, T)
                    # soundfile expects (time, channels) or (time,)
                    wav_cpu = wav.squeeze().float().cpu().numpy()
                    
                    sf.write(filepath, wav_cpu, 24000)
                    audio_files.append(filepath)
                    
                    # Calculate duration
                    duration = len(wav_cpu) / 24000
                    print(f"✓ Saved: {filepath} (Duration: {duration:.1f}s)")
                else:
                    print(f"✗ No audio generated for segment {segment_num}")
                
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
            'model': config.VIBE_VOICE_MODEL,
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
            reference_audio: Path to reference audio (Unused)
            reference_text_path: Path to reference text (Unused)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.model or not self.processor:
            print("⚠ VibeVoice not initialized")
            return False
        
        try:
            print(f"Generating audio...")
            
             # Load prompt if not already loaded
            if not hasattr(self, 'cached_prompt'):
                 if os.path.exists(config.VIBE_VOICE_PRESET_PATH):
                    print(f"Loading voice preset from {config.VIBE_VOICE_PRESET_PATH}")
                    self.cached_prompt = torch.load(config.VIBE_VOICE_PRESET_PATH, map_location=self.device, weights_only=False)
                 else:
                    print(f"⚠ Voice preset not found at {config.VIBE_VOICE_PRESET_PATH}")
                    self.cached_prompt = None

            if self.cached_prompt is None:
                 print("✗ No voice preset loaded, cannot generate audio")
                 return False

            inputs = self.processor.process_input_with_cached_prompt(
                    text=text,
                    cached_prompt=self.cached_prompt,
                    padding=True,
                    return_tensors="pt",
                    return_attention_mask=True,
            )
            
            # Move tensors
            for k, v in inputs.items():
                if torch.is_tensor(v):
                    inputs[k] = v.to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=None,
                    cfg_scale=1.5,
                    tokenizer=self.processor.tokenizer,
                    generation_config={'do_sample': False},
                     all_prefilled_outputs=copy.deepcopy(self.cached_prompt) if self.cached_prompt is not None else None
                )
            
            if outputs.speech_outputs and outputs.speech_outputs[0] is not None:
                wav = outputs.speech_outputs[0]
                
                # Convert to numpy for soundfile
                wav_cpu = wav.squeeze().float().cpu().numpy()
                sf.write(output_path, wav_cpu, 24000)
                
                duration = len(wav_cpu) / 24000
                print(f"✓ Audio saved: {output_path} (Duration: {duration:.1f}s)")
                return True
            else:
                print("✗ No audio generated")
                return False
            
        except Exception as e:
            print(f"✗ Failed to generate audio: {str(e)}")
            return False
    
    def is_available(self) -> bool:
        """Check if TTS is available and initialized"""
        return self.model is not None
