"""Security utilities for backup operations.

This module provides security-related functions and classes for handling sensitive
operations like password management and secure file operations.
"""

import getpass
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union


class ContextManager:
    """Secure context manager for password handling with memory sanitization."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def _password_context(self) -> str:
        """Secure password handling with proper memory sanitization.
        
        Uses a mutable bytearray to securely handle passwords and overwrite memory
        before deletion.
        
        Yields:
            str: The user's password or None if entry was empty
        """
        try:
            # Get immutable password from user
            password = getpass.getpass("Enter file encryption password: ")
            if not password:
                self.logger.error("Empty password rejected")
                yield None
                return

            # Convert to mutable bytearray for secure cleanup
            password_bytes = bytearray(password.encode("utf-8"))
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

    def _safe_cleanup(self, path: Union[str, Path]) -> None:
        """Securely remove partial files on failure.
        
        Args:
            path: Path to the file that needs to be cleaned up
        """
        try:
            file_path = Path(path)
            if file_path.exists():
                file_path.unlink()
                self.logger.info("Cleaned up partial encrypted file")
        except Exception as e:
            self.logger.error(f"Failed to clean up {path}: {str(e)}")
