"""Base manager for shared crypto operations.

This module contains the BaseCryptoManager class that provides
shared functionality for encryption and decryption operations using
the cryptography library with AES-256-GCM authenticated encryption.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from autotarcompress.utils.get_password import PasswordContext

if TYPE_CHECKING:
    from autotarcompress.config import BackupConfig


class BaseCryptoManager:
    """Base class for crypto operations with shared utilities.

    Provides common methods for file validation, hashing, key derivation,
    and secure cleanup used by both encryption and decryption managers.
    Uses AES-256-GCM for authenticated encryption with PBKDF2-HMAC-SHA256.
    """

    # Cryptographic constants (OWASP recommended)
    PBKDF2_ITERATIONS: int = 600000  # OWASP recommended minimum for PBKDF2
    SALT_SIZE: int = 16  # 128 bits for PBKDF2 salt
    NONCE_SIZE: int = 12  # 96 bits for AES-GCM nonce (recommended)
    KEY_SIZE: int = 32  # 256 bits for AES-256
    TAG_SIZE: int = 16  # 128 bits for GCM authentication tag

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

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2-HMAC-SHA256.

        Args:
            password: User password
            salt: Random salt (16 bytes)

        Returns:
            Derived 256-bit key for AES-256
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
        )
        return kdf.derive(password.encode("utf-8"))

    def _generate_salt(self) -> bytes:
        """Generate cryptographically secure random salt.

        Returns:
            Random 16-byte salt for PBKDF2
        """
        return secrets.token_bytes(self.SALT_SIZE)

    def _generate_nonce(self) -> bytes:
        """Generate cryptographically secure random nonce.

        Returns:
            Random 12-byte nonce for AES-GCM
        """
        return secrets.token_bytes(self.NONCE_SIZE)
