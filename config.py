"""
Configuration file for MathVizAI project
"""
import os
from dotenv import load_dotenv

# Load .env into environment variables (will look for .env in cwd/parents)
load_dotenv()

# API Configuration
# API Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL_NAME = "gpt-4o"

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
TTS_MODEL = "VibeVoice"
# TTS_REPO_PATH = r"c:\Users\aniru\Desktop\GitHub\neutts-air" # Deprecated
VIBE_VOICE_MODEL = "microsoft/VibeVoice-Realtime-0.5B"
VIBE_VOICE_PRESET_PATH = r"src/vibevoice/demo/voices/streaming_model/en-Carter_man.pt"
# AUDIO_SEGMENT_DURATION = (10, 30)  # Disabled: now content-driven
DEEP_DIVE_MODE = True  # Generate comprehensive, detailed content
AUDIO_FORMAT = "wav"
AUDIO_SAMPLE_RATE = 24000

# RAG Configuration
RAG_ENABLED = True
MAX_RAG_ITERATIONS = 6

# Default reference audio (in audio/ folder)
DEFAULT_REFERENCE_AUDIO = "sample_17s.wav"
DEFAULT_REFERENCE_TEXT = "transcript_17s.txt"

# Manim configuration
MANIM_QUALITY = "high"  # Options: low, medium, high, production
MANIM_FORMAT = "mp4"

# Performance
MAX_RENDER_WORKERS = 4  # Number of parallel rendering threads
MANIM_TIMEOUT = 1800    # 30 minutes timeout per scene (for deep-dive content)

