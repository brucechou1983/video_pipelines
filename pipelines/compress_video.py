"""
Compress video pipeline.
Compresses video by ~20x and converts to mp4.
"""

import subprocess
import re
from pathlib import Path

name = "Compress Video"
description = "Compress video by ~20x (downsizes resolution, lowers audio bitrate)"


def get_video_duration(input_path):
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(input_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return None


def process(input_path: str, output_dir: str, progress_callback=None) -> str:
    """
    Compress a video file by ~20x and convert to mp4.

    Args:
        input_path: Path to input video file
        output_dir: Directory to save output file
        progress_callback: Optional callback(percent, message) for progress updates

    Returns:
        Path to the compressed output file
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = output_dir / f"{input_path.stem}_compressed.mp4"

    # Get duration for progress calculation
    duration = get_video_duration(input_path)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vf", "scale=iw/2:ih/2:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264",
        "-crf", "28",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "64k",
        "-ar", "22050",
        "-progress", "pipe:1",
        str(output_path)
    ]

    if progress_callback:
        progress_callback(0, f"Starting compression: {input_path.name}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    time_pattern = re.compile(r'out_time_ms=(\d+)')

    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break

        match = time_pattern.search(line)
        if match and duration and progress_callback:
            current_time = int(match.group(1)) / 1_000_000
            percent = min(99, int((current_time / duration) * 100))
            progress_callback(percent, f"Compressing: {percent}%")

    returncode = process.wait()

    if returncode != 0:
        stderr = process.stderr.read()
        raise RuntimeError(f"ffmpeg compression failed: {stderr}")

    if progress_callback:
        progress_callback(100, "Compression complete")

    # Calculate compression stats
    input_size = input_path.stat().st_size
    output_size = output_path.stat().st_size
    ratio = input_size / output_size if output_size > 0 else 0

    if progress_callback:
        progress_callback(100, f"Done! {ratio:.1f}x smaller ({output_size / 1024 / 1024:.1f} MB)")

    return str(output_path)
