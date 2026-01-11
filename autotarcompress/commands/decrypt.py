"""Decryption command implementation for backup files.

This module contains the DecryptCommand class that handles the secure decryption
of encrypted backup archives using OpenSSL with PBKDF2.
"""

import logging

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig
from autotarcompress.decrypt_manager import DecryptManager


class DecryptCommand(Command):
    """Command to securely decrypt backup archives using OpenSSL with PBKDF2.

    This class ensures decryption parameters match those used for encryption and
    verifies file integrity post-decryption.
    """

    PBKDF2_ITERATIONS: int = 600000  # Must match encryption iterations

    def __init__(self, config: BackupConfig, file_path: str) -> None:
        """Initialize the DecryptCommand.

        Args:
            config (BackupConfig): The backup configuration object.
            file_path (str): Path to the encrypted file to decrypt.

        """
        self.config: BackupConfig = config
        self.file_path: str = file_path
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.manager = DecryptManager(config, self.logger)

    def execute(self) -> bool:
        """Perform secure decryption with matched PBKDF2 parameters.

        Returns:
            bool: True if decryption and integrity check succeed, False otherwise.

        """
        return self.manager.execute_decrypt(self.file_path)
