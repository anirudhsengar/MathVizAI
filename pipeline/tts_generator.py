"""
TTS Generator module - converts text to speech using Microsoft VibeVoice
"""
import sys
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
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


# Constants for phrase timing estimation
AVERAGE_SPEAKING_RATE = 2.8  # words per second (conversational pace)
MIN_PHRASE_DURATION = 1.5    # minimum seconds for a phrase
MAX_PHRASE_DURATION = 8.0    # maximum seconds for a phrase


def _estimate_word_duration(word: str) -> float:
    """Estimate duration of a single word based on syllable count approximation."""
    # Simple heuristic: ~0.35 seconds per word, with longer words taking more time
    base_duration = 0.35
    # Add extra time for longer words (rough syllable estimate)
    if len(word) > 8:
        base_duration += 0.1
    elif len(word) > 12:
        base_duration += 0.2
    return base_duration


def _split_into_phrases(text: str) -> List[str]:
    """
    Split text into natural phrases at sentence boundaries and clause markers.
    Phrases are 2-8 seconds when spoken, grouping short sentences together.
    """
    # Split at sentence boundaries first
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    phrases = []
    current_phrase = []
    current_word_count = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        words_in_sentence = len(sentence.split())
        
        # If sentence alone is too long, split at clause boundaries
        if words_in_sentence > int(MAX_PHRASE_DURATION * AVERAGE_SPEAKING_RATE):
            # Split at commas, semicolons, colons, dashes
            clauses = re.split(r'(?<=[,;:\—\–-])\s+', sentence)
            for clause in clauses:
                clause = clause.strip()
                if not clause:
                    continue
                clause_words = len(clause.split())
                
                if current_word_count + clause_words > int(MAX_PHRASE_DURATION * AVERAGE_SPEAKING_RATE):
                    if current_phrase:
                        phrases.append(' '.join(current_phrase))
                        current_phrase = []
                        current_word_count = 0
                
                current_phrase.append(clause)
                current_word_count += clause_words
                
                # If this clause alone is substantial, make it a phrase
                if current_word_count >= int(MIN_PHRASE_DURATION * AVERAGE_SPEAKING_RATE * 1.5):
                    phrases.append(' '.join(current_phrase))
                    current_phrase = []
                    current_word_count = 0
        else:
            # Check if adding this sentence would exceed max phrase length
            if current_word_count + words_in_sentence > int(MAX_PHRASE_DURATION * AVERAGE_SPEAKING_RATE):
                if current_phrase:
                    phrases.append(' '.join(current_phrase))
                    current_phrase = []
                    current_word_count = 0
            
            current_phrase.append(sentence)
            current_word_count += words_in_sentence
            
            # If we've reached a good phrase length, finalize it
            if current_word_count >= int(MIN_PHRASE_DURATION * AVERAGE_SPEAKING_RATE * 1.5):
                phrases.append(' '.join(current_phrase))
                current_phrase = []
                current_word_count = 0
    
    # Don't forget any remaining content
    if current_phrase:
        phrases.append(' '.join(current_phrase))
    
    return phrases


def estimate_phrase_timings(text: str, total_duration: float) -> List[Dict]:
    """
    Estimate phrase-level timings for text based on word count distribution.
    
    Args:
        text: The full text of the audio segment
        total_duration: Actual duration of the generated audio in seconds
    
    Returns:
        List of phrase dictionaries with 'text', 'start', 'end', 'duration' keys
    """
    phrases = _split_into_phrases(text)
    
    if not phrases:
        return [{'text': text, 'start': 0.0, 'end': total_duration, 'duration': total_duration}]
    
    # Calculate word counts for each phrase
    phrase_word_counts = [len(p.split()) for p in phrases]
    total_words = sum(phrase_word_counts)
    
    if total_words == 0:
        # Edge case: no words, just return the full duration
        return [{'text': text, 'start': 0.0, 'end': total_duration, 'duration': total_duration}]
    
    # Distribute duration proportionally based on word count
    phrase_timings = []
    current_time = 0.0
    
    for phrase_text, word_count in zip(phrases, phrase_word_counts):
        # Calculate duration proportionally
        proportion = word_count / total_words
        phrase_duration = total_duration * proportion
        
        phrase_timings.append({
            'text': phrase_text,
            'start': round(current_time, 3),
            'end': round(current_time + phrase_duration, 3),
            'duration': round(phrase_duration, 3)
        })
        
        current_time += phrase_duration
    
    # Ensure last phrase ends exactly at total_duration
    if phrase_timings:
        phrase_timings[-1]['end'] = round(total_duration, 3)
        phrase_timings[-1]['duration'] = round(total_duration - phrase_timings[-1]['start'], 3)
    
    return phrase_timings




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
    ) -> List[Dict]:
        """
        Generate audio for each segment with phrase-level timing data.
        
        Args:
            segments: List of segment dictionaries with 'number' and 'audio' keys
            file_manager: File manager instance
            reference_audio: Path to reference audio (optional)
            reference_text: Path to reference text (optional)
        
        Returns:
            List of segment result dictionaries containing:
            - 'audio_file': path to generated audio
            - 'segment_number': segment number
            - 'duration': total audio duration in seconds
            - 'text': original text
            - 'phrases': list of phrase timing dicts with {text, start, end, duration}
        """
        if not self.model or not self.processor:
            print("\n" + "="*60)
            print("TTS GENERATOR - SKIPPED")
            print("="*60)
            print("⚠ VibeVoice not available. Audio generation skipped.")
            return []
        
        print(f"\n{'='*60}")
        print(f"TTS GENERATOR (VibeVoice) - With Phrase Timing")
        print(f"{'='*60}")
        
        # Generate audio for each segment
        segment_results = []
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
                    
                    # Calculate duration
                    duration = len(wav_cpu) / 24000
                    
                    # Estimate phrase-level timings
                    phrase_timings = estimate_phrase_timings(text, duration)
                    
                    print(f"✓ Saved: {filepath} (Duration: {duration:.1f}s, Phrases: {len(phrase_timings)})")
                    
                    # Build segment result with phrase timing data
                    segment_result = {
                        'audio_file': filepath,
                        'segment_number': segment_num,
                        'duration': round(duration, 3),
                        'text': text,
                        'phrases': phrase_timings
                    }
                    segment_results.append(segment_result)
                    
                else:
                    print(f"✗ No audio generated for segment {segment_num}")
                
            except Exception as e:
                print(f"✗ Failed to generate segment {segment_num}: {str(e)}")
                continue
        
        print(f"\n{'='*60}")
        print(f"✓ Generated {len(segment_results)}/{total_segments} audio files with phrase timing")
        print(f"{'='*60}\n")
        
        # Save metadata about generated audio (including phrase timings)
        audio_metadata = {
            'total_segments': total_segments,
            'generated': len(segment_results),
            'model': config.VIBE_VOICE_MODEL,
            'sample_rate': 24000,
            'files': [os.path.basename(r['audio_file']) for r in segment_results],
            'segment_details': segment_results
        }
        file_manager.save_json(audio_metadata, 'audio_metadata.json', 'audio')
        
        return segment_results

    
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
