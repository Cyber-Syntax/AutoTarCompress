"""Security module for handling sensitive operations.

This module provides security-related functions and classes for handling
sensitive data like passwords and secure file operations.

Features:
- Password confirmation to prevent user mistakes
- Secure memory cleanup
- User-friendly feedback with emoji indicators
- Protection against empty passwords
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
        """Yield password securely with confirmation.

        Ensures memory is sanitized after use.

        Yields:
            str | None: The user's password, or None if entry was empty
                       or confirmation failed.

        """
        password_bytes: bytearray | None = None
        confirm_bytes: bytearray | None = None
        try:
            # Get password first time
            password: str = getpass.getpass("Enter file encryption password: ")
            if not password:
                self.logger.error("Empty password rejected")
                print("❌ Password cannot be empty")
                yield None
                return None

            # Get password confirmation
            confirm_password: str = getpass.getpass("Confirm encryption password: ")
            if password != confirm_password:
                self.logger.error("Password confirmation failed")
                print("❌ Passwords do not match. Please try again.")
                yield None
                return None

            print("✅ Password confirmed successfully")
            password_bytes = bytearray(password.encode("utf-8"))
            confirm_bytes = bytearray(confirm_password.encode("utf-8"))
            yield password_bytes.decode("utf-8")

        finally:
            # Securely overwrite the memory for both passwords
            if password_bytes is not None:
                mv = memoryview(password_bytes)
                mv[:] = b"\x00" * len(mv)
                del password_bytes

            if confirm_bytes is not None:
                mv = memoryview(confirm_bytes)
                mv[:] = b"\x00" * len(mv)
                del confirm_bytes

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
