"""AutoTarCompress package.

This package provides a complete backup solution with encryption capabilities.
"""

from pathlib import Path

import tomllib

try:
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)
    __version__ = data.get("project", {}).get("version", "unknown")
except (OSError, ValueError):
    __version__ = "unknown"
