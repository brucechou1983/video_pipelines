# Video Pipelines

macOS app for batch video processing with drag-and-drop support.

## Setup

```bash
brew install ffmpeg uv
./run.sh
```

Or use the app bundle: `open "Video Pipelines.app"`

## Adding Pipelines

Create a Python file in `pipelines/` folder:

```python
name = "My Pipeline"
description = "What it does"

def process(input_path, output_dir, progress_callback=None):
    # Your processing logic
    return output_path
```

Restart the app to see new pipelines.
