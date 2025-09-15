"""Security module for handling sensitive operations.

This module provides security-related functions and classes for handling
sensitive data like passwords and secure file operations.
"""

import getpass
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


class ContextManager:
    """Secure context manager for password handling and safe cleanup."""

    def __init__(self) -> None:
        """Initialize ContextManager with logger."""
        self.logger: logging.Logger = logging.getLogger(__name__)

    @contextmanager
    def _password_context(self) -> Generator[str | None, None, None]:
        """Yield password securely, ensuring memory is sanitized after use.

        Yields:
            str | None: The user's password, or None if entry was empty.

        """
        password_bytes: bytearray | None = None
        try:
            password: str = getpass.getpass("Enter file encryption password: ")
            if not password:
                self.logger.error("Empty password rejected")
                yield None
                return None
            password_bytes = bytearray(password.encode("utf-8"))
            yield password_bytes.decode("utf-8")

        finally:
            # Securely overwrite the memory
            if password_bytes is not None:
                # Overwrite each byte with zero
                for i in range(len(password_bytes)):
                    password_bytes[i] = 0
                # Clear reference
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
        except (OSError, PermissionError) as e:
            self.logger.error("Failed to clean up %s: %s", path, e)
