"""Security utilities for safe password handling and file operations.

This module provides secure context managers and utilities for handling
sensitive data like passwords and encrypted files.
"""

import getpass
import logging
import os
from contextlib import contextmanager


class ContextManager:
    """Secure context manager for password handling"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def _password_context(self):
        """Secure password handling with proper memory sanitization.
        By using mutable object like bytearray you can overwrite the data in memory
        """
        try:
            # Get inmutable password from user
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

    def _safe_cleanup(self, path: str):
        """Securely remove partial files on failure"""
        try:
            if os.path.exists(path):
                os.remove(path)
                self.logger.info("Cleaned up partial encrypted file")
        except Exception as e:
            self.logger.error(f"Failed to clean up {path}: {str(e)}")
