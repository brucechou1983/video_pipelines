"""
Application settings management with persistent storage.
"""

import json
from pathlib import Path
from typing import Any

# Settings file location
SETTINGS_DIR = Path.home() / ".config" / "video_pipelines"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

# Default settings
DEFAULT_SETTINGS = {
    "worker_count": 4,
    "optional_pipelines": {
        "extract_midi": {
            "enabled": False,
            "installed": False,
        }
    },
    "pipeline_options": {},
}


def ensure_settings_dir():
    """Ensure settings directory exists."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    """Load settings from disk, creating default if needed."""
    ensure_settings_dir()

    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            # Merge with defaults to handle new settings
            return merge_settings(DEFAULT_SETTINGS, settings)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Failed to load settings: {e}")
            return DEFAULT_SETTINGS.copy()

    return DEFAULT_SETTINGS.copy()


def merge_settings(defaults: dict, current: dict) -> dict:
    """Merge current settings with defaults, preserving current values."""
    result = defaults.copy()

    for key, value in current.items():
        if key in result:
            if isinstance(value, dict) and isinstance(result[key], dict):
                result[key] = merge_settings(result[key], value)
            else:
                result[key] = value
        else:
            result[key] = value

    return result


def save_settings(settings: dict):
    """Save settings to disk."""
    ensure_settings_dir()

    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except IOError as e:
        print(f"Failed to save settings: {e}")


def get_setting(key: str, default: Any = None) -> Any:
    """Get a specific setting value."""
    settings = load_settings()
    keys = key.split('.')
    value = settings

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value


def set_setting(key: str, value: Any):
    """Set a specific setting value."""
    settings = load_settings()
    keys = key.split('.')

    # Navigate to parent
    current = settings
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    current[keys[-1]] = value
    save_settings(settings)


def is_optional_pipeline_enabled(pipeline_key: str) -> bool:
    """Check if an optional pipeline is enabled."""
    return get_setting(f"optional_pipelines.{pipeline_key}.enabled", False)


def is_optional_pipeline_installed(pipeline_key: str) -> bool:
    """Check if an optional pipeline is installed."""
    return get_setting(f"optional_pipelines.{pipeline_key}.installed", False)


def set_optional_pipeline_enabled(pipeline_key: str, enabled: bool):
    """Set whether an optional pipeline is enabled."""
    set_setting(f"optional_pipelines.{pipeline_key}.enabled", enabled)


def set_optional_pipeline_installed(pipeline_key: str, installed: bool):
    """Set whether an optional pipeline is installed."""
    set_setting(f"optional_pipelines.{pipeline_key}.installed", installed)
