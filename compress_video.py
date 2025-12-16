#!/usr/bin/env python3
"""
Compress video by ~20x and convert to mp4.
- Downsizes resolution to 1/4
- Lowers audio sample rate and bitrate
"""

import subprocess
import sys
import os
from pathlib import Path


def compress_video(input_path: str, output_path: str = None) -> str:
    """
    Compress a video file by ~20x and convert to mp4.

    Args:
        input_path: Path to input video file
        output_path: Optional output path. If not provided, creates {input}_compressed.mp4

    Returns:
        Path to the compressed output file
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_compressed.mp4"
    else:
        output_path = Path(output_path)

    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-i", str(input_path),
        # Video: scale to 1/2 size, ensure even dimensions for h264
        "-vf", "scale=iw/2:ih/2:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264",
        "-crf", "28",  # Quality (higher = smaller file, lower quality)
        "-preset", "fast",
        # Audio: 10x volume boost, lower sample rate and bitrate
        "-af", "volume=10.0",
        "-c:a", "aac",
        "-b:a", "64k",
        "-ar", "22050",
        str(output_path)
    ]

    print(f"Compressing: {input_path}")
    print(f"Output: {output_path}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        raise RuntimeError("ffmpeg compression failed")

    # Show size comparison
    input_size = input_path.stat().st_size
    output_size = output_path.stat().st_size
    ratio = input_size / output_size

    print(f"\nDone!")
    print(f"  Input:  {input_size / 1024 / 1024:.1f} MB")
    print(f"  Output: {output_size / 1024 / 1024:.1f} MB")
    print(f"  Ratio:  {ratio:.1f}x smaller")

    return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input_video> [output_video]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        compress_video(input_file, output_file)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
