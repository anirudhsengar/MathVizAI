
import sys
import os
from manim import *

# Add src to path to import visual_utils
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from visual_utils import create_glowing_text

class Outro(Scene):
    def construct(self):
        # Audio
        audio_file = "outro_audio.wav"
        if os.path.exists(audio_file):
            self.add_sound(audio_file)
        else:
            print(f"Warning: {audio_file} not found. Running without audio.")

        # Visuals
        # Background
        self.camera.background_color = "#0f0f1a"  # Keeping dark background

        # Text
        thank_you = create_glowing_text("Thank you for watching!", font_size=72, color=WHITE, glow_color=BLUE)
        thank_you.move_to(ORIGIN)
        
        # Animations
        self.play(FadeIn(thank_you), run_time=1.0)
        
        # Wait for audio to finish
        self.wait(5)
        
        # No FadeOut to ensure last frame is captured for fallback
