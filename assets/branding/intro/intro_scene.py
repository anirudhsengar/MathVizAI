
import sys
import os
from manim import *

# Add src to path to import visual_utils
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from visual_utils import create_glowing_text, create_cyberpunk_box

class Intro(Scene):
    def construct(self):
        # Visuals
        self.camera.background_color = "#0f0f1a"

        # Text
        math_text = create_glowing_text("Math", font_size=84, color=BLUE, glow_color=BLUE_A)
        viz_text = create_glowing_text("Viz", font_size=84, color=TEAL, glow_color=TEAL_A)
        
        # Position
        math_text.move_to(LEFT * 1.2)
        viz_text.next_to(math_text, RIGHT, buff=0.1)
        
        group = VGroup(math_text, viz_text).move_to(ORIGIN)

        # Animation: stylized generation
        # 1. Write the text
        self.play(
            Write(math_text, run_time=1.0),
            Write(viz_text, run_time=1.0),
            lag_ratio=0.1
        )
        
        # 2. Add a flash or pulse
        self.play(
            math_text.animate.set_color(WHITE),
            viz_text.animate.set_color(WHITE),
            rate_func=there_and_back,
            run_time=0.5
        )
        
        # 3. Wait to fill 3-4 seconds total
        self.wait(1.5)
