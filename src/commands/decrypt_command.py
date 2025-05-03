"""Decryption command implementation for backup files.

This module contains the DecryptCommand class that handles the secure decryption
of encrypted backup archives using OpenSSL with PBKDF2.
"""

import hashlib
import logging
import os
import re
import subprocess
from typing import Optional

from src.commands.command import Command
from src.config import BackupConfig
from src.security import ContextManager


class DecryptCommand(Command):
    """Concrete command to perform decryption with secure parameters"""

    PBKDF2_ITERATIONS = 600000  # Must match encryption iterations

    def __init__(self, config: BackupConfig, file_path: str):
        self.config = config
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)
        self._password_context = ContextManager()._password_context
        self._safe_cleanup = ContextManager()._safe_cleanup

    def execute(self) -> bool:
        """Secure decryption with matched PBKDF2 parameters"""
        output_path = os.path.splitext(self.file_path)[0]
        decrypted_path = f"{output_path}-decrypted"

        with self._password_context() as password:
            if not password:
                return False

            cmd = [
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
                self._verify_integrity(decrypted_path)
                return True
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Decryption failed: {self._sanitize_logs(e.stderr)}")
                self._safe_cleanup(decrypted_path)
                return False

    def _verify_integrity(self, decrypted_path: str) -> None:
        """Verify decrypted file matches original backup checksum"""
        original_path = os.path.splitext(self.file_path)[0]
        if os.path.exists(original_path):
            decrypted_hash = self._calculate_sha256(decrypted_path)
            original_hash = self._calculate_sha256(original_path)

            # Compare hashes
            print(f"Decrypted file hash: {decrypted_hash}")
            print(f"Original file hash: {original_hash}")

            if decrypted_hash == original_hash:
                self.logger.info("Integrity verified: SHA256 match")
            else:
                self.logger.error("Integrity check failed")

    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 checksum for a file"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()

    def _sanitize_logs(self, output: bytes) -> str:
        """Safe log sanitization without modifying bytes"""
        sanitized = output.replace(b"password=", b"password=[REDACTED]")
        sanitized = re.sub(rb"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", b"[IP_REDACTED]", sanitized)
        return sanitized.decode("utf-8", errors="replace")