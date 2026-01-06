"""Backup command implementation for creating compressed archives.

This module contains the BackupCommand class that orchestrates backup creation
using the BackupManager for core backup operations.
"""

import logging

from autotarcompress.backup_manager import BackupManager
from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig


class BackupCommand(Command):
    """Command to create compressed backup archives."""

    def __init__(self, config: BackupConfig) -> None:
        """Initialize BackupCommand.

        Args:
            config (BackupConfig): Backup configuration object.

        """
        self.config: BackupConfig = config
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.manager = BackupManager(config, self.logger)

    def execute(self) -> bool:
        """Execute backup process.

        Returns:
            bool: True if backup succeeded, False otherwise.

        """
        return self.manager.execute_backup()
