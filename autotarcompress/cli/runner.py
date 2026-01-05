"""CLI orchestration utilities for AutoTarCompress.

This module contains helpers for the CLI layer including config initialization
and utility functions for file operations.
"""

from __future__ import annotations

import logging
import os

import typer

from autotarcompress.config import BackupConfig
from autotarcompress.logger import (
    setup_application_logging,
    setup_basic_logging,
)

# Date format validation constant
DATE_PARTS_COUNT = 3

logger = logging.getLogger(__name__)


def find_file_by_date(files: list[str], target_date: str) -> str | None:
    """Find backup file by date pattern.

    Args:
        files: List of backup files.
        target_date: Date in dd-mm-yyyy format.

    Returns:
        Matching filename or None if not found.

    """
    try:
        date_parts = target_date.split("-")
        if len(date_parts) != DATE_PARTS_COUNT:
            raise ValueError("Invalid date format")

        day, month, year = date_parts
        date_pattern = f"{day}-{month}-{year}"

        for file in files:
            if date_pattern in file:
                return file
    except ValueError:
        typer.echo(
            f"Error: Invalid date format '{target_date}'. Use dd-mm-yyyy"
        )

    return None


def initialize_config() -> BackupConfig:
    """Initialize configuration and logging for the application.

    Returns:
        BackupConfig: Loaded or newly created config instance.
    """
    config = BackupConfig.load()

    if not os.path.exists(config.config_path):
        # Basic logging for initial setup
        setup_basic_logging()
        logger.info("No configuration found. Creating defaults.")
        config = BackupConfig.create_default()
        logger.warning("⚠️  Default config created at %s", config.config_path)
        logger.warning(
            "⚠️  Please edit the config file and add directories to backup"
        )
        logger.info("To edit: nano %s", config.config_path)
        logger.info("Add your directories under the 'dirs_to_backup' setting")

    # Setup logging with configured level
    setup_application_logging(config.get_log_level())
    return config


def get_backup_files(backup_folder: str) -> list[str]:
    """Get list of backup files in the specified folder."""
    expanded_backup_dir: str = os.path.expanduser(backup_folder)
    return [
        f
        for f in os.listdir(expanded_backup_dir)
        if f.endswith(".tar.xz") and not f.endswith(".enc")
    ]


def get_encrypted_files(backup_folder: str) -> list[str]:
    """Get list of encrypted backup files in the specified folder."""
    expanded_backup_dir: str = os.path.expanduser(backup_folder)
    return [f for f in os.listdir(expanded_backup_dir) if f.endswith(".enc")]
