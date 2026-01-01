
import sys
import os

# Add root directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline.tts_generator import TTSGenerator
import config

def main():
    # Double check config is loaded correctly
    print(f"Using Voice Preset from Config: {config.VIBE_VOICE_PRESET_PATH}")
    print(f"Using TTS Model from Config: {config.VIBE_VOICE_MODEL}")

    # Text for the outro
    OUTRO_TEXT = "Thank you for watching! I hope you found this visualization helpful. Stay tuned for more math and physics content coming soon, and don't forget to subscribe!"
    OUTPUT_FILE = "outro_audio.wav"

    # Initialize Generator
    generator = TTSGenerator()
    
    if not generator.is_available():
        print("Error: TTS Generator is not available.")
        sys.exit(1)

    # Generate Audio
    print("Generating audio using project pipeline...")
    success = generator.generate_single_audio(
        text=OUTRO_TEXT,
        output_path=OUTPUT_FILE
    )

    if success:
        print(f"Audio generated successfully at {OUTPUT_FILE}")
    else:
        print("Audio generation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
