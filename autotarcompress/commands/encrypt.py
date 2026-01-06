"""Encryption command implementation for securing backup files.

This module contains the EncryptCommand class that handles the secure
encryption of backup archives using OpenSSL with PBKDF2.

Features:
- Password confirmation for user safety
- User-friendly success/failure notifications
- Secure memory cleanup
- PBKDF2 encryption with 600,000 iterations
"""

import logging

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig
from autotarcompress.encrypt_manager import EncryptManager


class EncryptCommand(Command):
    """Concrete command to perform encryption.

    Using OpenSSL with secure PBKDF2 implementation.
    fd:0 is used to pass password securely without exposing in process list.
    Root user can still see the password in process list.
    After the process is done, the password is deleted from memory.
    """

    PBKDF2_ITERATIONS: int = 600000  # OWASP recommended minimum

    def __init__(self, config: BackupConfig, file_to_encrypt: str) -> None:
        """Initialize EncryptCommand.

        Args:
            config (BackupConfig): Backup configuration object.
            file_to_encrypt (str): Path to the file to encrypt.

        """
        self.file_to_encrypt: str = file_to_encrypt
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.manager = EncryptManager(config, self.logger)

    def execute(self) -> bool:
        """Perform secure PBKDF2 encryption with OpenSSL.

        Returns:
            bool: True if encryption succeeded, False otherwise.

        """
        return self.manager.execute_encrypt(self.file_to_encrypt)
