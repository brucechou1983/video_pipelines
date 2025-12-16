# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

```bash
# Run the app (requires ffmpeg)
./run.sh

# Or run directly with uv
uv run python app.py

# Or use the app bundle
open "Video Pipelines.app"
```

**Prerequisite:** `brew install ffmpeg`

## Architecture

This is a PyQt6 macOS desktop app for batch video processing with drag-and-drop support.

### Core Components

- **app.py** - Main application with PyQt6 GUI (VideoProcessorApp, DropZone, ProcessingThread)
- **pipelines/** - Plugin directory for video processing pipelines, auto-discovered at startup

### Pipeline System

Pipelines are discovered via `pipelines/__init__.py:get_available_pipelines()` which scans the pipelines directory for modules with `name` and `process` attributes.

Pipeline interface:
```python
name = "Pipeline Name"
description = "What it does"

def process(input_path: str, output_dir: str, progress_callback=None) -> str:
    # progress_callback(percent, message) for UI updates
    return output_path
```

Output files are saved to the same directory as the source file.

### Threading Model

ProcessingThread (QThread) handles batch processing in background. Emits signals for progress, completion, and errors back to the main UI thread.
