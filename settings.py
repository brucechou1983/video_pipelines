"""
Application settings management with persistent storage.
"""

import json
import os
import tempfile
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


def ensure_settings_dir() -> bool:
    """
    Ensure settings directory exists.

    Returns:
        True if directory exists or was created, False on permission error
    """
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except (PermissionError, OSError) as e:
        print(f"Failed to create settings directory: {e}")
        return False


def load_settings() -> dict:
    """Load settings from disk, creating default if needed."""
    if not ensure_settings_dir():
        return DEFAULT_SETTINGS.copy()

    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    # Empty file, return defaults
                    return DEFAULT_SETTINGS.copy()
                settings = json.loads(content)
                if not isinstance(settings, dict):
                    # Invalid format, return defaults
                    print("Settings file has invalid format, using defaults")
                    return DEFAULT_SETTINGS.copy()
            # Merge with defaults to handle new settings
            return merge_settings(DEFAULT_SETTINGS, settings)
        except json.JSONDecodeError as e:
            print(f"Failed to parse settings file: {e}")
            # Backup corrupted file
            _backup_corrupted_settings()
            return DEFAULT_SETTINGS.copy()
        except (IOError, PermissionError) as e:
            print(f"Failed to read settings file: {e}")
            return DEFAULT_SETTINGS.copy()

    return DEFAULT_SETTINGS.copy()


def _backup_corrupted_settings():
    """Backup a corrupted settings file before overwriting."""
    try:
        if SETTINGS_FILE.exists():
            backup_path = SETTINGS_FILE.with_suffix('.json.bak')
            SETTINGS_FILE.rename(backup_path)
            print(f"Backed up corrupted settings to {backup_path}")
    except (IOError, PermissionError) as e:
        print(f"Failed to backup corrupted settings: {e}")


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


def save_settings(settings: dict) -> bool:
    """
    Save settings to disk atomically.

    Returns:
        True if save succeeded, False otherwise
    """
    if not ensure_settings_dir():
        return False

    try:
        # Write to temp file first, then rename for atomic operation
        fd, temp_path = tempfile.mkstemp(
            dir=str(SETTINGS_DIR),
            prefix='.settings_',
            suffix='.tmp'
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)

            # Atomic rename
            os.replace(temp_path, SETTINGS_FILE)
            return True
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
    except (IOError, PermissionError, OSError) as e:
        print(f"Failed to save settings: {e}")
        return False


def get_setting(key: str, default: Any = None) -> Any:
    """Get a specific setting value using dot notation."""
    try:
        settings = load_settings()
        keys = key.split('.')
        value = settings

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value
    except Exception as e:
        print(f"Error getting setting '{key}': {e}")
        return default


def set_setting(key: str, value: Any) -> bool:
    """
    Set a specific setting value using dot notation.

    Returns:
        True if setting was saved successfully, False otherwise
    """
    try:
        settings = load_settings()
        keys = key.split('.')

        if not keys:
            return False

        # Navigate to parent, creating intermediate dicts as needed
        current = settings
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value
        return save_settings(settings)
    except Exception as e:
        print(f"Error setting '{key}': {e}")
        return False


def is_optional_pipeline_enabled(pipeline_key: str) -> bool:
    """Check if an optional pipeline is enabled."""
    return get_setting(f"optional_pipelines.{pipeline_key}.enabled", False)


def is_optional_pipeline_installed(pipeline_key: str) -> bool:
    """Check if an optional pipeline is installed."""
    return get_setting(f"optional_pipelines.{pipeline_key}.installed", False)


def set_optional_pipeline_enabled(pipeline_key: str, enabled: bool) -> bool:
    """Set whether an optional pipeline is enabled."""
    return set_setting(f"optional_pipelines.{pipeline_key}.enabled", enabled)


def set_optional_pipeline_installed(pipeline_key: str, installed: bool) -> bool:
    """Set whether an optional pipeline is installed."""
    return set_setting(f"optional_pipelines.{pipeline_key}.installed", installed)
