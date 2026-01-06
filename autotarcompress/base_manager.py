"""Base manager for shared crypto operations.

This module contains the BaseCryptoManager class that provides
shared functionality for encryption and decryption operations.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from autotarcompress.utils.get_password import PasswordContext

if TYPE_CHECKING:
    from autotarcompress.config import BackupConfig


class BaseCryptoManager:
    """Base class for crypto operations with shared utilities.

    Provides common methods for file validation, hashing, logging sanitization,
    and secure cleanup used by both encryption and decryption managers.
    """

    PBKDF2_ITERATIONS: int = 600000  # OWASP recommended minimum

    def __init__(
        self, config: BackupConfig, logger: logging.Logger | None = None
    ) -> None:
        """Initialize BaseCryptoManager.

        Args:
            config: Backup configuration
            logger: Logger instance (optional, creates default if not provided)
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._password_context = PasswordContext()._password_context
        self._safe_cleanup = PasswordContext()._safe_cleanup

    def _validate_input_file(self, file_path: str) -> bool:
        """Validate input file exists and is not empty.

        Args:
            file_path: Path to the file to validate

        Returns:
            True if file is valid, False otherwise
        """
        path = Path(file_path)
        if not path.is_file():
            self.logger.error("File not found: %s", file_path)
            return False
        if path.stat().st_size == 0:
            self.logger.error(
                "Cannot process empty file (potential tampering attempt)"
            )
            return False
        return True

    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 checksum for a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA256 hex digest of the file contents
        """
        sha256 = hashlib.sha256()
        with Path(file_path).open("rb") as file_obj:
            while True:
                data = file_obj.read(65536)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()

    def _sanitize_logs(self, output: bytes) -> str:
        """Sanitize log output to redact sensitive information.

        Args:
            output: Raw stderr output from subprocess

        Returns:
            Sanitized string safe for logging
        """
        # Redact password and IP addresses from logs for security
        sanitized = re.sub(rb"password=[^\s]*", b"password=[REDACTED]", output)
        sanitized = re.sub(
            rb"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
            b"[IP_REDACTED]",
            sanitized,
        )
        return sanitized.decode("utf-8", errors="replace")
