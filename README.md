# Video Pipelines for Mac

A free, open-source macOS application for batch video compression and audio-to-MIDI conversion. Simple drag-and-drop interface with no watermarks or file size limits.

## Features

### 🎬 Video Compressor for Mac

Compress large video files on your Mac with ease:

- **Reduce video file size by up to 20x** — perfect for sharing via email or messaging apps
- **Batch processing** — drag and drop multiple files at once
- **Configurable settings** — adjust resolution scale, audio bitrate, and volume
- **Preserves quality** — uses H.264 encoding with smart compression
- **Fast processing** — optimized for Apple Silicon and Intel Macs
- Supports MP4, MOV, AVI, MKV, and more

### 🎹 Extract MIDI from Audio (Audio-to-MIDI Converter)

Convert audio recordings to MIDI files using AI:

- **Powered by Spotify's basic-pitch** — state-of-the-art AI model for music transcription
- **Works with video and audio files** — extract MIDI from MP4, MP3, WAV, FLAC, and more
- **Piano/melody extraction** — ideal for transcribing melodies and piano recordings
- **Adjustable sensitivity** — presets for clean output or capturing every note
- **CoreML optimized** — fast inference on Apple Silicon Macs

## Installation

### Requirements

- macOS 10.15 or later
- [Homebrew](https://brew.sh)

### Quick Start

```bash
# Install dependencies
brew install ffmpeg uv

# Run the app
./run.sh
```

Or use the pre-built app bundle:

```bash
open "Video Pipelines.app"
```

### MIDI Extraction Setup

The MIDI extraction feature requires an additional one-time installation:

1. Open the app and go to **Settings** (⌘,)
2. Enable the "Extract MIDI" pipeline
3. Click "Install" to download the AI model

## Usage

1. Launch Video Pipelines
2. Select a pipeline (Compress Video or Extract MIDI)
3. Drag and drop your files onto the window
4. Processed files are saved alongside the originals

## Adding Custom Pipelines

Create a Python file in the `pipelines/` folder:

```python
name = "My Pipeline"
description = "What it does"

def process(input_path, output_dir, progress_callback=None):
    # Your processing logic
    return output_path
```

Restart the app to load new pipelines.

## Keywords

`mac video compressor` · `compress video on mac` · `reduce video file size mac` · `audio to midi mac` · `extract midi from mp3` · `convert audio to midi` · `free video compression tool macos` · `batch video converter mac` · `music transcription software mac`

## License

MIT
