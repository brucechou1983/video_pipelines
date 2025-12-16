"""
Video processing pipelines module.
Each pipeline should define:
- name: Display name for the pipeline
- description: What the pipeline does
- process(input_path, output_dir, progress_callback) -> output_path

Optional attributes:
- optional: If True, pipeline must be enabled in settings to appear
- requires_install: If True, pipeline requires dependency installation
- options: List of configurable options
"""

from pathlib import Path
import importlib
import pkgutil


def get_available_pipelines(include_disabled_optional=False):
    """
    Discover and return all available pipelines.

    Args:
        include_disabled_optional: If True, include optional pipelines even if disabled

    Returns:
        Dict of pipeline_key -> pipeline info dict
    """
    # Import settings here to avoid circular imports
    import settings as app_settings

    pipelines = {}
    package_dir = Path(__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if module_name.startswith('_'):
            continue
        try:
            module = importlib.import_module(f'.{module_name}', package=__name__)
            if hasattr(module, 'name') and hasattr(module, 'process'):
                # Check if this is an optional pipeline
                is_optional = getattr(module, 'optional', False)

                if is_optional and not include_disabled_optional:
                    # Check if enabled in settings
                    if not app_settings.is_optional_pipeline_enabled(module_name):
                        continue

                pipelines[module_name] = {
                    'name': module.name,
                    'description': getattr(module, 'description', ''),
                    'process': module.process,
                    'options': getattr(module, 'options', None),
                    'optional': is_optional,
                    'requires_install': getattr(module, 'requires_install', False),
                }
        except Exception as e:
            print(f"Failed to load pipeline {module_name}: {e}")

    return pipelines
