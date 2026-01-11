"""AutoTarCompress package.

This package provides a complete backup solution with encryption capabilities.
"""

from importlib.metadata import PackageNotFoundError, version

# Expose managers for direct imports
from autotarcompress.backup_manager import BackupManager
from autotarcompress.cleanup_manager import CleanupManager
from autotarcompress.extract_manager import ExtractManager
from autotarcompress.info_manager import InfoManager

try:
    # "autotarcompress" should match the 'name' field in your pyproject.toml
    __version__ = version("autotarcompress")
except PackageNotFoundError:
    # This happens if the package isn't installed (e.g., running raw scripts)
    __version__ = "dev"


__all__ = ["BackupManager", "CleanupManager", "ExtractManager", "InfoManager"]
