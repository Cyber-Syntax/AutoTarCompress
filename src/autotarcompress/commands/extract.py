"""Extract command implementation for backup archives.

This module contains the ExtractCommand class that handles the extraction
of compressed backup archives.
"""

import logging

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig
from autotarcompress.extract_manager import ExtractManager


class ExtractCommand(Command):
    """Command to extract tar.xz and tar.zst backup archives securely."""

    def __init__(self, config: BackupConfig, file_path: str) -> None:
        """Initialize ExtractCommand.

        Args:
            config (BackupConfig): Backup configuration object.
            file_path (str): Path to the archive to extract.

        """
        self.config: BackupConfig = config
        self.file_path: str = file_path
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.manager = ExtractManager(config, self.logger)

    def execute(self) -> bool:
        """Extract the specified archive to a directory.

        Returns:
            bool: True if extraction succeeded, False otherwise.

        """
        return self.manager.execute_extract(self.file_path)
