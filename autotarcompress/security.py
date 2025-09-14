"""Security utilities for backup operations.

This module provides security-related functions and classes for handling sensitive
operations like password management and secure file operations.
"""

import getpass
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Union


class ContextManager:
    """Secure context manager for password handling and safe cleanup."""

    def __init__(self) -> None:
        """Initialize ContextManager with logger."""
        self.logger: logging.Logger = logging.getLogger(__name__)

    @contextmanager
    def _password_context(self) -> str:
        """Yield password securely, ensuring memory is sanitized after use.

        Yields:
            str: The user's password, or None if entry was empty.

        """
        try:
            password: str = getpass.getpass("Enter file encryption password: ")
            if not password:
                self.logger.error("Empty password rejected")
                yield None
                return
            password_bytes: bytearray = bytearray(password.encode("utf-8"))
            yield password_bytes.decode("utf-8")

        finally:
            # Securely overwrite the memory
            if "password_bytes" in locals():
                # Overwrite each byte with zero
                for i in range(len(password_bytes)):
                    password_bytes[i] = 0
                # Prevent compiler optimizations from skipping the loop
                password_bytes = None
                del password_bytes

    def _safe_cleanup(self, path: str | Path) -> None:
        """Remove partial files on failure, logging the result.

        Args:
            path (str | Path): Path to the file that needs to be cleaned up.

        """
        try:
            file_path: Path = Path(path)
            if file_path.exists():
                file_path.unlink()
                self.logger.info("Cleaned up partial encrypted file")
        except Exception as e:
            self.logger.error("Failed to clean up %s: %s", path, e)
