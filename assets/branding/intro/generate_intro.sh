#!/bin/bash
# Generate Intro Video (No Audio)

# Video config (High Quality 1080p60)
QUALITY="-pqh --fps 60"
SCENE_FILE="intro_scene.py"
SCENE_NAME="Intro"
OUTPUT_DIR="media/videos/intro_scene/1080p60"
OUTPUT_FILE="$OUTPUT_DIR/Intro.mp4"

# Clean up previous output
rm -f "$OUTPUT_FILE"

# 1. Attempt standard generation
echo "Attempting standard Manim generation..."
manim $QUALITY $SCENE_FILE $SCENE_NAME

if [ -f "$OUTPUT_FILE" ]; then
    echo "Standard generation successful."
    if ffprobe "$OUTPUT_FILE" >/dev/null 2>&1; then
        echo "Video is valid! Location: $OUTPUT_FILE"
        exit 0
    fi
    echo "Standard generation produced invalid video. Trying fallback..."
fi

# 2. Fallback: PNG Sequence + FFMPEG
echo "Standard generation failed. Using PNG sequence fallback..."

# Generate PNG sequence
# --format=png outputs individual frames
manim $QUALITY --format=png $SCENE_FILE $SCENE_NAME

# The images are usually stored in media/images/intro_scene/
IMAGE_DIR="media/images/intro_scene"

# Check if image directory exists and has files
if [ ! -d "$IMAGE_DIR" ]; then
    echo "Error: Image directory not found at $IMAGE_DIR"
    exit 1
fi

COUNT=$(find "$IMAGE_DIR" -name "*.png" | wc -l)
if [ "$COUNT" -eq 0 ]; then
    echo "Error: No PNG images generated."
    exit 1
fi

echo "Found $COUNT frames."

# Adaptive framerate
# If we have ~90 frames, Manim rendered 30fps (3s * 30). Stitch at 30fps.
# If we have ~180 frames, Manim rendered 60fps (3s * 60). Stitch at 60fps.
if [ "$COUNT" -lt 120 ]; then
    FPS=30
    echo "Frame count suggests 30fps rendering. Stitching at 30fps..."
else
    FPS=60
    echo "Frame count suggests 60fps rendering. Stitching at 60fps..."
fi

# FFMPEG Stitching
# -pattern_type glob -i "*.png": Read all pngs
# -c:v libx264 -pix_fmt yuv420p: Standard MP4 encoding
ffmpeg -y -framerate $FPS -pattern_type glob -i "$IMAGE_DIR/Intro*.png" -c:v libx264 -pix_fmt yuv420p "$OUTPUT_FILE"

if [ -f "$OUTPUT_FILE" ]; then
    echo "Fallback verification..."
    if ffprobe "$OUTPUT_FILE" >/dev/null 2>&1; then
        echo "Fallback successful! Video ready at: $OUTPUT_FILE"
        # Cleanup images to save space
        rm -rf "$IMAGE_DIR"
        exit 0
    else
        echo "Fallback video is invalid."
        exit 1
    fi
else
    echo "Fallback failed. Output file not created."
    exit 1
fi
