"""Encryption command implementation for securing backup files.

This module contains the EncryptCommand class that handles the secure
encryption of backup archives using OpenSSL with PBKDF2.
"""

import logging
import os
import re
import subprocess
from typing import Tuple

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig
from autotarcompress.security import ContextManager


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
        self._password_context = ContextManager()._password_context
        self._safe_cleanup = ContextManager()._safe_cleanup
        self.required_openssl_version: Tuple[int, int, int] = (3, 0, 0)

    def execute(self) -> bool:
        """Perform secure PBKDF2 encryption with OpenSSL.

        Returns:
            bool: True if encryption succeeded, False otherwise.

        """
        if not self._validate_input_file():
            return False

        with self._password_context() as password:
            if not password:
                return False
            return self._run_encryption_process(password)

    def _validate_input_file(self) -> bool:
        """Validate input file exists and is not empty.

        Returns:
            bool: True if file is valid, False otherwise.

        """
        if not os.path.isfile(self.file_to_encrypt):
            self.logger.error("File not found: %s", self.file_to_encrypt)
            return False
        if os.path.getsize(self.file_to_encrypt) == 0:
            self.logger.error("Cannot encrypt empty file (potential tampering attempt)")
            return False
        return True

    def _run_encryption_process(self, password: str) -> bool:
        """Run encryption process with OpenSSL PBKDF2 parameters.

        Args:
            password (str): Password for encryption.

        Returns:
            bool: True if encryption succeeded, False otherwise.

        """
        output_path: str = f"{self.file_to_encrypt}.enc"
        cmd: list[str] = [
            "openssl",
            "enc",
            "-aes-256-cbc",
            "-a",
            "-salt",
            "-pbkdf2",
            "-iter",
            str(self.PBKDF2_ITERATIONS),
            "-in",
            self.file_to_encrypt,
            "-out",
            output_path,
            "-pass",
            "fd:0",
        ]

        try:
            result = subprocess.run(
                cmd,
                input=f"{password}\n".encode(),
                check=True,
                stderr=subprocess.PIPE,
                timeout=300,
                shell=False,
            )
            self.logger.debug("Encryption success: %s", self._sanitize_logs(result.stderr))
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error("Encryption failed: %s", self._sanitize_logs(e.stderr))
            self._safe_cleanup(output_path)
            return False
        except subprocess.TimeoutExpired:
            self.logger.error("Encryption timed out")
            self._safe_cleanup(output_path)
            return False

    def _sanitize_logs(self, output: bytes) -> str:
        """Safe log sanitization without modifying bytes."""
        # Replace password=<value> with password=[REDACTED]
        sanitized = re.sub(rb"password=[^\s]*", b"password=[REDACTED]", output)
        sanitized = re.sub(
            rb"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
            b"[IP_REDACTED]",
            sanitized,
        )
        return sanitized.decode("utf-8", errors="replace")
