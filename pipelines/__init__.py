"""
Video processing pipelines module.
Each pipeline should define:
- name: Display name for the pipeline
- description: What the pipeline does
- process(input_path, output_dir, progress_callback) -> output_path
"""

from pathlib import Path
import importlib
import pkgutil

def get_available_pipelines():
    """Discover and return all available pipelines."""
    pipelines = {}
    package_dir = Path(__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if module_name.startswith('_'):
            continue
        try:
            module = importlib.import_module(f'.{module_name}', package=__name__)
            if hasattr(module, 'name') and hasattr(module, 'process'):
                pipelines[module_name] = {
                    'name': module.name,
                    'description': getattr(module, 'description', ''),
                    'process': module.process
                }
        except Exception as e:
            print(f"Failed to load pipeline {module_name}: {e}")

    return pipelines
