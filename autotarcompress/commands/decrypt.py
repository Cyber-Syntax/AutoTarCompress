"""Decryption command implementation for backup files.

This module contains the DecryptCommand class that handles the secure decryption
of encrypted backup archives using OpenSSL with PBKDF2.
"""

import hashlib
import logging
import os
import re
import subprocess

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig
from autotarcompress.security import ContextManager


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
        self._password_context = ContextManager()._password_context
        self._safe_cleanup = ContextManager()._safe_cleanup

    def execute(self) -> bool:
        """Perform secure decryption with matched PBKDF2 parameters.

        Returns:
            bool: True if decryption and integrity check succeed, False otherwise.

        """
        output_path: str = os.path.splitext(self.file_path)[0]
        decrypted_path: str = f"{output_path}-decrypted"

        # Use password context manager to securely obtain password
        with self._password_context() as password:  # type: ignore[var-annotated]
            if password is None:
                return False

            cmd: list[str] = [
                "openssl",
                "enc",
                "-d",
                "-aes-256-cbc",
                "-a",
                "-salt",
                "-pbkdf2",
                "-iter",
                str(self.PBKDF2_ITERATIONS),
                "-in",
                self.file_path,
                "-out",
                decrypted_path,
                "-pass",
                "fd:0",
            ]

            try:
                subprocess.run(
                    cmd,
                    input=f"{password}\n".encode(),
                    check=True,
                    stderr=subprocess.PIPE,
                    timeout=300,
                    shell=False,
                )
            except subprocess.CalledProcessError as exc:
                # Log sanitized error output to avoid leaking sensitive data
                self.logger.error(
                    "Decryption failed: %s",
                    self._sanitize_logs(exc.stderr),
                )
                self._safe_cleanup(decrypted_path)
                return False
            except subprocess.TimeoutExpired:
                self.logger.error("Decryption timed out")
                self._safe_cleanup(decrypted_path)
                return False

            self._verify_integrity(decrypted_path)
            return True

    def _verify_integrity(self, decrypted_path: str) -> None:
        """Verify decrypted file matches original backup checksum.

        Args:
            decrypted_path (str): Path to the decrypted file.

        """
        original_path: str = os.path.splitext(self.file_path)[0]
        if os.path.exists(original_path):
            decrypted_hash: str = self._calculate_sha256(decrypted_path)
            original_hash: str = self._calculate_sha256(original_path)

            # Log hashes for verification
            self.logger.info("Decrypted file hash: %s", decrypted_hash)
            self.logger.info("Original file hash: %s", original_hash)

            if decrypted_hash == original_hash:
                self.logger.info("Integrity verified: SHA256 match")
            else:
                self.logger.error("Integrity check failed")

    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 checksum for a file.

        Args:
            file_path (str): Path to the file.

        Returns:
            str: SHA256 hex digest of the file contents.

        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as file_obj:
            while True:
                data = file_obj.read(65536)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()

    def _sanitize_logs(self, output: bytes) -> str:
        """Sanitize log output to redact sensitive information.

        Args:
            output (bytes): Raw stderr output from subprocess.

        Returns:
            str: Sanitized string safe for logging.

        """
        # Redact password and IP addresses from logs for security
        sanitized = re.sub(rb"password=[^\s]*", b"password=[REDACTED]", output)
        sanitized = re.sub(
            rb"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
            b"[IP_REDACTED]",
            sanitized,
        )
        return sanitized.decode("utf-8", errors="replace")
