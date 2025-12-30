# MathVizAI

**Fully Automated Mathematical Video Generation System**

MathVizAI is a complete end-to-end system that takes mathematical problems and automatically generates polished educational videos with synchronized visualizations and audio narration. The entire pipeline is automated from problem input to final video output.

![MathVizAI](image.png)

## Features

- **Intelligent Problem Solving**: Uses LLM to solve complex mathematical problems with detailed proofs
- **Automated Validation**: Self-correcting system with evaluator that ensures solution accuracy
- **Natural Audio Scripts**: Generates conversational explanations optimized for text-to-speech
- **Voice Cloning TTS**: neuTTS-air integration for natural voice narration
- **Automated Video Rendering**: Renders all Manim scenes with quality settings
- **Audio-Video Synchronization**: Aligns audio with video and adjusts durations automatically
- **Text Slide Generation**: Creates text slides when video is missing
- **Beautiful Visualizations**: Creates Manim animations that sync with narration
- **Segmented Output**: Breaks content into 15-20 second segments for optimal processing
- **Multiple Scene Support**: Handles complex problems with unlimited animation scenes
- **Final Video Assembly**: Concatenates all segments into one polished video
- **Live Web Research**: Optional Tavily-powered search for fresh references and visual inspiration

## Pipeline Architecture

```
Query Input: "Solve x² + 5x + 6 = 0"
    ↓
┌─────────────────────┐
│   Math Solver       │ ← Solves problem with proof
└─────────────────────┘
    ↓
┌─────────────────────┐
│   Solution          │ ← Validates correctness
│   Evaluator         │   (Auto-retry until perfect)
└─────────────────────┘
    ↓
┌─────────────────────┐
│   Script Writer     │ ← Creates audio narration
└─────────────────────┘   (15-20s segments)
    ↓
┌─────────────────────┐
│   Video Generator   │ ← Generates Manim code
└─────────────────────┘   (multiple scenes)
    ↓
┌─────────────────────┐
│   TTS Generator     │ ← Creates audio files
└─────────────────────┘   (voice cloning)
    ↓
┌─────────────────────┐
│   Video Renderer    │ ← Renders all scenes
└─────────────────────┘   (automated)
    ↓
┌─────────────────────┐
│   Video             │ ← Syncs audio + video
│   Synchronizer      │   (duration matching)
└─────────────────────┘   (text slides for missing video)
    ↓
  Final Polished Video
   (ready to publish)
```

## Installation

### Prerequisites

- Python 3.8 or higher
- GitHub Token with API access
- FFmpeg (required for Manim video rendering)
- Manim (optional, for automated video rendering)
- neuTTS-air (optional, for audio generation)

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/anirudhsengar/MathVizAI.git
cd MathVizAI
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**

Create a `.env` file or set environment variables:

```powershell
# Windows PowerShell
$env:OPENAI_API_KEY = "your_openai_key"
$env:TAVILY_API_KEY = "your_tavily_key"
$env:GITHUB_TOKEN = "your_github_token_here"

# Linux/Mac
export OPENAI_API_KEY="your_openai_key"
export TAVILY_API_KEY="your_tavily_key"
export GITHUB_TOKEN="your_github_token_here"
```

Alternatively, create a `.env` file:
```
OPENAI_API_KEY=your_openai_key
TAVILY_API_KEY=your_tavily_key
GITHUB_TOKEN=your_github_token_here
```

4. **Optional: Install Manim for automated video rendering**
```bash
pip install manim
```

For detailed Manim installation instructions, visit: https://docs.manim.community/en/stable/installation.html

**FFmpeg Installation (required for Manim):**
- Windows: `choco install ffmpeg` or download from https://ffmpeg.org/
- Linux: `sudo apt install ffmpeg`
- Mac: `brew install ffmpeg`

5. **Optional: Set up neuTTS-air for audio generation**

See [TTS_SETUP.md](TTS_SETUP.md) for detailed instructions.

Quick setup:
```powershell
# Install soundfile
pip install soundfile

# Clone and install neuTTS-air
git clone https://github.com/anirudhsengar/neutts-air.git
cd neutts-air
pip install -e .
```

Note: TTS is optional. Without it, the system will generate all other components and skip audio generation.

## Usage

### Basic Usage

```bash
python main.py
```
Then enter mathematical problems when prompted:

```
Enter math problem: Prove that the square root of 2 is irrational
```

### Output Structure

Each query generates a timestamped folder in `output/` with:

```
output/
└── 20250118_143022_Prove_that_the_square_root_of_2/
    ├── metadata.json              # Session metadata
    ├── original_query.txt         # Your original question
    ├── solver/
    │   ├── solution_attempt_1.txt
    │   └── solution_final.txt     # Approved solution
    ├── evaluator/
    │   ├── evaluation_attempt_1.txt
    │   └── evaluation_final.txt   # Final validation report
    ├── script/
    │   ├── audio_script.txt       # Complete script
    │   ├── segments.json          # Parsed segments
    │   └── segment_XX_visual.txt  # Visual cues
    ├── audio/
    │   ├── segment_01.wav         # Generated audio (if TTS enabled)
    │   ├── segment_02.wav
    │   ├── segment_XX_audio.txt   # Audio script text
    │   └── audio_metadata.json    # Audio generation info
    ├── video/
    │   ├── manim_visualization.py # Executable Manim code
    │   └── rendering_instructions.txt
    └── final/
        └── (final video will go here)
```

### Rendering the Video

After generation, render the Manim visualization:

```bash
cd output/[your_session_folder]/video
manim -qh manim_visualization.py MathVisualization
```

Quality options:
- `-ql`: Low quality (480p15) - fast preview
- `-qm`: Medium quality (720p30)
- `-qh`: High quality (1080p60) - recommended
- `-qk`: Production quality (1440p60)

## Configuration

Edit `config.py` to customize:

```python
# Temperature settings for each component
TEMPERATURE_SOLVER = 0.4          # Solution generation
TEMPERATURE_EVALUATOR = 0.0       # Strict evaluation
TEMPERATURE_SCRIPT_WRITER = 0.6   # Creative narration
TEMPERATURE_VIDEO_GENERATOR = 0.2 # Consistent code

# Retry settings
MAX_SOLVER_RETRIES = 5  # Max attempts before accepting solution

# Video settings
VIDEO_RESOLUTION = "1080p"
VIDEO_FPS = 60
```

## Roadmap

### Current Status

- Mathematical problem solving with proofs
- Automated solution validation with retry logic
- Audio script generation with segments
- Manim visualization code generation
- TTS audio generation (neuTTS-air integration)
- Audio-video synchronization
- Final video assembly

### Planned Features

- Background music and sound effects
- Subtitle generation
- Batch processing mode
- Web interface

## Development

### Project Structure

```
MathVizAI/
├── main.py                 # Entry point
├── config.py              # Configuration
├── requirements.txt       # Dependencies
├── system_prompts/        # LLM prompts
│   ├── solver.txt
│   ├── evaluator.txt
│   ├── script_writer.txt
│   └── video_generator.txt
├── pipeline/              # Core pipeline modules
│   ├── orchestrator.py    # Main pipeline controller
│   ├── solver.py          # Math solver
│   ├── evaluator.py       # Solution validator
│   ├── script_writer.py   # Audio script generator
│   └── video_generator.py # Manim code generator
├── utils/                 # Utility modules
│   ├── llm_client.py      # LLM API wrapper
│   ├── prompt_loader.py   # Prompt management
│   └── file_manager.py    # File operations
└── output/                # Generated content
```

### Adding New Features

1. **Custom Prompts**: Edit files in `system_prompts/` to customize AI behavior
2. **Pipeline Stages**: Add new stages in `pipeline/` directory
3. **Configuration**: Add settings to `config.py`

## Examples

Example problems you can try:

- "Prove that the square root of 2 is irrational"
- "Solve the integral of e^x * sin(x) dx"
- "Prove the Pythagorean theorem using similar triangles"
- "Find the derivative of x^x"
- "Explain the Fundamental Theorem of Calculus"

## Contributing

Contributions are welcome! Areas where help is needed:

- TTS integration (neuTTS-air)
- Audio-video synchronization
- Manim animation templates
- Additional visualization types
- Testing and bug fixes

## License

MIT License

## Acknowledgments

- **Manim Community** - Mathematical animation engine
- **Microsoft Phi-4** - Reasoning model via GitHub Models
- **Azure AI Inference** - LLM API infrastructure

