"""Encryption command implementation for securing backup files.

This module contains the EncryptCommand class that handles the secure encryption
of backup archives using OpenSSL with PBKDF2.
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
    """Concrete command to perform encryption
    using OpenSSL with secure PBKDF2 implementation
    fd:0 is used to pass password securely without exposing in process list
    root user can still see the password in process list
    after the process is done, the password is deleted from memory
    """

    PBKDF2_ITERATIONS = 600000  # OWASP recommended minimum

    def __init__(self, config: BackupConfig, file_to_encrypt: str):
        self.file_to_encrypt = file_to_encrypt
        self.logger = logging.getLogger(__name__)
        self._password_context = ContextManager()._password_context
        self._safe_cleanup = ContextManager()._safe_cleanup

        self.required_openssl_version: Tuple[int, int, int] = (
            3,
            0,
            0,
        )  # Argon2id requires OpenSSL 3.0+

    def execute(self) -> bool:
        """Secure PBKDF2 implementation with proper OpenSSL syntax"""
        if not self._validate_input_file():
            return False

        with self._password_context() as password:
            if not password:
                return False

            return self._run_encryption_process(password)

    def _validate_input_file(self) -> bool:
        """Validate input file meets security requirements"""
        if not os.path.isfile(self.file_to_encrypt):
            self.logger.error(f"File not found: {self.file_to_encrypt}")
            return False

        if os.path.getsize(self.file_to_encrypt) == 0:
            self.logger.error("Cannot encrypt empty file (potential tampering attempt)")
            return False

        return True

    def _run_encryption_process(self, password: str) -> bool:
        """Core encryption process with proper OpenSSL parameters"""
        output_path = f"{self.file_to_encrypt}.enc"

        cmd = [
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
            self.logger.debug(f"Encryption success: {self._sanitize_logs(result.stderr)}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Encryption failed: {self._sanitize_logs(e.stderr)}")
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
        sanitized = re.sub(rb"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", b"[IP_REDACTED]", sanitized)
        return sanitized.decode("utf-8", errors="replace")
