"""
MIDI Extraction Pipeline.
Extract piano MIDI from audio/video files using Spotify's basic-pitch.
"""

import subprocess
import tempfile
from pathlib import Path

name = "Extract MIDI"
description = "Extract piano MIDI from audio/video using basic-pitch"

# Mark this as an optional pipeline that requires installation
optional = True
requires_install = True

# Pipeline options
options = [
    {
        'key': 'preset',
        'label': 'Preset',
        'type': 'choice',
        'default': 'clean',
        'choices': [
            ('default', 'Default - Balanced detection'),
            ('clean', 'Clean - Fewer false notes'),
            ('sensitive', 'Sensitive - Capture all notes'),
            ('custom', 'Custom - Manual tuning'),
        ],
        'description': 'Quick preset for common use cases'
    },
    {
        'key': 'melodia_trick',
        'label': 'Melodia Cleanup',
        'type': 'bool',
        'default': True,
        'description': 'Apply melodia post-processing to reduce spurious notes'
    },
    {
        'key': 'onset_threshold',
        'label': 'Onset Threshold',
        'type': 'float',
        'default': 0.5,
        'min': 0.0,
        'max': 1.0,
        'step': 0.05,
        'description': 'Minimum confidence for note onset detection (0.0-1.0)'
    },
    {
        'key': 'frame_threshold',
        'label': 'Frame Threshold',
        'type': 'float',
        'default': 0.3,
        'min': 0.0,
        'max': 1.0,
        'step': 0.05,
        'description': 'Minimum confidence for note frame detection (0.0-1.0)'
    },
    {
        'key': 'min_note_length',
        'label': 'Min Note Length (ms)',
        'type': 'int',
        'default': 58,
        'min': 10,
        'max': 500,
        'description': 'Minimum note duration in milliseconds'
    },
]

# Presets for easy configuration
PRESETS = {
    'default': {
        'onset_threshold': 0.5,
        'frame_threshold': 0.3,
        'min_note_length': 58,
        'melodia_trick': True,
    },
    'clean': {
        'onset_threshold': 0.6,
        'frame_threshold': 0.5,
        'min_note_length': 127,
        'melodia_trick': True,
    },
    'sensitive': {
        'onset_threshold': 0.3,
        'frame_threshold': 0.2,
        'min_note_length': 30,
        'melodia_trick': False,
    },
}


def check_installation() -> tuple[bool, str]:
    """
    Check if basic-pitch is installed.

    Returns:
        Tuple of (is_installed, message)
    """
    try:
        # Use importlib.metadata to check package version without importing it
        # (importing basic_pitch can fail due to TensorFlow initialization issues)
        from importlib.metadata import version, PackageNotFoundError
        try:
            ver = version("basic-pitch")
            return True, f"basic-pitch {ver}"
        except PackageNotFoundError:
            return False, "basic-pitch not installed"
    except Exception as e:
        # Fallback: try direct import
        try:
            import basic_pitch
            return True, f"basic-pitch {getattr(basic_pitch, '__version__', 'installed')}"
        except ImportError:
            return False, "basic-pitch not installed"
        except Exception:
            # Package exists but has import issues (likely TF related)
            return True, "basic-pitch installed (TF init pending)"


def install_dependencies(progress_callback=None) -> tuple[bool, str]:
    """
    Install basic-pitch and dependencies.

    Returns:
        Tuple of (success, message)
    """
    import shutil

    if progress_callback:
        progress_callback(10, "Installing basic-pitch (this may take a few minutes)...")

    try:
        # Try uv first (preferred for this project), then fall back to pip
        # Use CoreML backend for Apple Silicon Macs (faster and more compatible)
        # Pin exact versions for reproducibility and compatibility
        uv_path = shutil.which("uv")
        packages = [
            "setuptools>=70.0.0",
            "scipy>=1.13.0,<1.14",  # 1.14+ removed scipy.signal.gaussian
            "basic-pitch[coreml]==0.4.0",
        ]
        if uv_path:
            # Use --reinstall to force downgrade scipy if needed
            cmd = [uv_path, "pip", "install", "--reinstall"] + packages
        else:
            # Fallback to pip
            import sys
            cmd = [sys.executable, "-m", "pip", "install", "--force-reinstall"] + packages

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode != 0:
            return False, f"Installation failed: {result.stderr}"

        # Log warnings if any (even on success)
        if result.stderr and progress_callback:
            progress_callback(85, "Installation completed with warnings")

        if progress_callback:
            progress_callback(90, "Verifying installation...")

        # Verify installation
        is_installed, msg = check_installation()
        if is_installed:
            if progress_callback:
                progress_callback(100, "Installation complete!")
            return True, "basic-pitch installed successfully"
        else:
            return False, "Installation completed but verification failed"

    except subprocess.TimeoutExpired:
        return False, "Installation timed out"
    except Exception as e:
        return False, f"Installation error: {str(e)}"


def extract_audio(input_path: Path, output_path: Path, progress_callback=None) -> bool:
    """
    Extract audio from video file using ffmpeg.

    Args:
        input_path: Path to input video/audio file
        output_path: Path for output WAV file
        progress_callback: Optional progress callback

    Returns:
        True if successful
    """
    if progress_callback:
        progress_callback(5, "Extracting audio...")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # PCM 16-bit
        "-ar", "22050",  # Sample rate (basic-pitch expects 22050)
        "-ac", "1",  # Mono
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr}")

    return True


def process(input_path: str, output_dir: str, progress_callback=None, options=None) -> str:
    """
    Extract MIDI from audio/video file.

    Args:
        input_path: Path to input audio/video file
        output_dir: Directory to save output MIDI file
        progress_callback: Optional callback(percent, message) for progress updates
        options: Optional dict of pipeline options

    Returns:
        Path to the output MIDI file
    """
    # Import here to catch import errors at runtime
    try:
        from basic_pitch.inference import predict_and_save
        from basic_pitch import ICASSP_2022_MODEL_PATH as MODEL_PATH
    except ImportError as e:
        raise RuntimeError(
            f"basic-pitch is not installed. Please enable and install it from Settings (Cmd+,). Error: {e}"
        )
    except Exception as e:
        # Catch other errors (e.g., TensorFlow/CoreML initialization issues)
        raise RuntimeError(
            f"Failed to initialize basic-pitch: {type(e).__name__}: {e}"
        )

    input_path = Path(input_path)
    output_dir = Path(output_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Get options with defaults
    opts = options or {}

    # Apply preset if selected (unless custom)
    preset = opts.get('preset', 'clean')
    if preset != 'custom' and preset in PRESETS:
        preset_values = PRESETS[preset]
        onset_threshold = preset_values['onset_threshold']
        frame_threshold = preset_values['frame_threshold']
        min_note_length = preset_values['min_note_length']
        melodia_trick = preset_values['melodia_trick']
    else:
        # Custom mode - use individual settings
        onset_threshold = opts.get('onset_threshold', 0.5)
        frame_threshold = opts.get('frame_threshold', 0.3)
        min_note_length = opts.get('min_note_length', 58)
        melodia_trick = opts.get('melodia_trick', True)

    if progress_callback:
        progress_callback(0, f"Starting MIDI extraction: {input_path.name}")

    # Check if input is video or audio
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpeg', '.mpg'}
    audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma'}

    is_video = input_path.suffix.lower() in video_extensions
    is_audio = input_path.suffix.lower() in audio_extensions

    if not is_video and not is_audio:
        raise ValueError(f"Unsupported file format: {input_path.suffix}")

    # Use temp directory for intermediate files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Extract audio if input is video
        if is_video:
            audio_path = temp_dir / f"{input_path.stem}.wav"
            extract_audio(input_path, audio_path, progress_callback)
        else:
            # For audio files, convert to WAV if needed
            if input_path.suffix.lower() != '.wav':
                audio_path = temp_dir / f"{input_path.stem}.wav"
                extract_audio(input_path, audio_path, progress_callback)
            else:
                audio_path = input_path

        if progress_callback:
            progress_callback(20, "Running MIDI extraction (this may take a while)...")

        # Output MIDI path
        output_midi = output_dir / f"{input_path.stem}_midi.mid"

        # Run basic-pitch prediction
        # predict_and_save saves to a directory, so we'll use temp output then move
        temp_output_dir = temp_dir / "output"
        temp_output_dir.mkdir(exist_ok=True)

        if progress_callback:
            progress_callback(30, "Analyzing audio with AI model...")

        try:
            predict_and_save(
                audio_path_list=[str(audio_path)],
                output_directory=str(temp_output_dir),
                save_midi=True,
                sonify_midi=False,
                save_model_outputs=False,
                save_notes=False,
                model_or_model_path=MODEL_PATH,
                onset_threshold=onset_threshold,
                frame_threshold=frame_threshold,
                minimum_note_length=min_note_length,
                melodia_trick=melodia_trick,
            )
        except Exception as e:
            raise RuntimeError(f"MIDI extraction failed: {str(e)}")

        if progress_callback:
            progress_callback(90, "Saving MIDI file...")

        # Find the generated MIDI file
        generated_midi = temp_output_dir / f"{audio_path.stem}_basic_pitch.mid"

        if not generated_midi.exists():
            # Try alternative naming
            midi_files = list(temp_output_dir.glob("*.mid"))
            if midi_files:
                generated_midi = midi_files[0]
            else:
                raise RuntimeError("MIDI file was not generated")

        # Move to final destination
        import shutil
        shutil.move(str(generated_midi), str(output_midi))

    if progress_callback:
        progress_callback(100, f"MIDI extraction complete: {output_midi.name}")

    return str(output_midi)
