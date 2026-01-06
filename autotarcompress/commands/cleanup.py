"""Cleanup command for managing old backup files.

This module contains the CleanupCommand class that handles the deletion
of old backup files according to retention policies.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from autotarcompress.cleanup_manager import CleanupManager
from autotarcompress.commands.command import Command

if TYPE_CHECKING:
    from autotarcompress.config import BackupConfig


class CleanupCommand(Command):
    """Command to clean up old backup, encrypted, and decrypted files."""

    def __init__(
        self, config: BackupConfig, cleanup_all: bool = False
    ) -> None:
        """Initialize CleanupCommand.

        Args:
            config (BackupConfig): Backup configuration with retention and
                folder settings.
            cleanup_all (bool): If True, delete all backup files regardless
                of retention policy.

        """
        self.config: BackupConfig = config
        self.cleanup_all: bool = cleanup_all
        self.manager: CleanupManager = CleanupManager(config)
        self.logger: logging.Logger = logging.getLogger(__name__)

    def execute(self) -> bool:
        """Delete old backup, encrypted, and decrypted files.

        Per retention policy or all files if cleanup_all is True.

        Returns:
            bool: Always True (cleanup always completes, even if nothing
                to delete).

        """
        return self.manager.execute_cleanup(self.cleanup_all)
