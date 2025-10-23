"""
Configuration file for MathVizAI project
"""
import os
from dotenv import load_dotenv

# Load .env into environment variables (will look for .env in cwd/parents)
load_dotenv()

# API Configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
ENDPOINT = "https://models.github.ai/inference"
MODEL_NAME = "microsoft/Phi-4"

# Temperature settings for different tasks
TEMPERATURE_SOLVER = 0.4
TEMPERATURE_EVALUATOR = 0.0
TEMPERATURE_SCRIPT_WRITER = 0.6
TEMPERATURE_VIDEO_GENERATOR = 0.2

# Token limits
MAX_TOKENS = 4000
TOP_P = 1.0

# System prompt paths
SOLVER_PROMPT_PATH = "system_prompts/solver.txt"
EVALUATOR_PROMPT_PATH = "system_prompts/evaluator.txt"
SCRIPT_WRITER_PROMPT_PATH = "system_prompts/script_writer.txt"
VIDEO_GENERATOR_PROMPT_PATH = "system_prompts/video_generator.txt"

# Output configuration
OUTPUT_DIR = "output"
MAX_SOLVER_RETRIES = 5  # Maximum retries for solver-evaluator loop

# Video configuration
VIDEO_RESOLUTION = "1080p"
VIDEO_FPS = 60
VIDEO_BACKGROUND = "BLACK"

# Audio configuration
TTS_MODEL = "neuTTS-air"
TTS_REPO_PATH = r"c:\Users\aniru\Desktop\GitHub\neutts-air"
AUDIO_SEGMENT_DURATION = (5, 15)  # Min and max seconds per segment
AUDIO_FORMAT = "wav"
AUDIO_SAMPLE_RATE = 24000

# Default reference audio (in audio/ folder)
DEFAULT_REFERENCE_AUDIO = "sample_17s.wav"
DEFAULT_REFERENCE_TEXT = "transcript_17s.txt"

# Manim configuration
MANIM_QUALITY = "high"  # Options: low, medium, high, production
MANIM_FORMAT = "mp4"
