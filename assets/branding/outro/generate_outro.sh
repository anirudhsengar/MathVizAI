#!/bin/bash
# set -e # Don't exit on error, handle it

# 1. Generate Audio
echo "Generating Audio..."
python generate_outro_audio.py

if [ ! -f "outro_audio.wav" ]; then
    echo "Error: Audio generation failed. outro_audio.wav not found."
    exit 1
fi

# 2. Generate Video
echo "Generating Video..."
manim -pqh outro_scene.py Outro

VIDEO_FILE="media/videos/outro_scene/1080p60/Outro.mp4"

if [ -f "$VIDEO_FILE" ]; then
    echo "Manim video generated. Verifying..."
    if ffprobe "$VIDEO_FILE" >/dev/null 2>&1; then
        echo "Video is valid!"
        exit 0
    else
        echo "Video is invalid/corrupted."
    fi
else
    echo "Manim video generation failed."
fi

# 3. Fallback: Static Image + Audio
echo "Attempting fallback: Static Image + Audio..."
# -s saves the last frame. -o specifies filename relative to media/images/...
manim -pqh -s outro_scene.py Outro

# Find the generated image. Usually media/images/outro_scene/Outro_ManimCE_v0.19.0.png
IMAGE_FILE=$(find media/images/outro_scene -name "*.png" | head -n 1)

if [ -z "$IMAGE_FILE" ]; then
    echo "Error: Static image generation failed."
    exit 1
fi

echo "Found image: $IMAGE_FILE"
echo "Combining with audio..."

ffmpeg -y -loop 1 -i "$IMAGE_FILE" -i outro_audio.wav -c:v libx264 -c:a aac -tune zerolatency -shortest -pix_fmt yuv420p "$VIDEO_FILE"

if [ -f "$VIDEO_FILE" ]; then
    echo "Fallback successful! Video created at $VIDEO_FILE"
else
    echo "Fallback failed."
    exit 1
fi
