"""Info command implementation for displaying last backup information.

This module contains the InfoCommand class that displays information about
the last backup operation.
"""

import logging

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig
from autotarcompress.info_manager import InfoManager


class InfoCommand(Command):
    """Command to display last backup information from backup info file."""

    def __init__(self, config: BackupConfig) -> None:
        """Initialize InfoCommand.

        Args:
            config (BackupConfig): Backup configuration object.

        """
        self.config: BackupConfig = config
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.manager: InfoManager = InfoManager(config, self.logger)

    def execute(self) -> bool:
        """Display last backup information if available.

        Returns:
            bool: True if info displayed, False otherwise.

        """
        return self.manager.execute_info()
