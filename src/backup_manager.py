"""Backup manager implementation.

This module forwards imports from other modules for backward compatibility.
"""

# Re-export BackupConfig from config.py
from src.config import BackupConfig

__all__ = ["BackupConfig"]
