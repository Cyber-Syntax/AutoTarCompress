"""AutoTarCompress package.

This package provides a complete backup solution with encryption capabilities.
"""

import tomllib
from pathlib import Path

try:
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)
    __version__ = data.get("project", {}).get("version", "unknown")
except (OSError, ValueError):
    __version__ = "unknown"

# Expose managers for direct imports
from autotarcompress.backup_manager import BackupManager
from autotarcompress.cleanup_manager import CleanupManager
from autotarcompress.extract_manager import ExtractManager
from autotarcompress.info_manager import InfoManager

__all__ = ["BackupManager", "CleanupManager", "ExtractManager", "InfoManager"]
