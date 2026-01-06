"""Encrypt manager for handling encryption operations.

This module contains the EncryptManager class that encapsulates
the core encryption logic.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from autotarcompress.base_manager import BaseCryptoManager


class EncryptManager(BaseCryptoManager):
    """Manager class for encryption operations.

    Handles the core encryption logic including password management,
    OpenSSL operations, and hash embedding for integrity.
    """

    def execute_encrypt(self, file_to_encrypt: str) -> bool:
        """Execute the complete encryption process with embedded hash.

        Args:
            file_to_encrypt: Path to the file to encrypt

        Returns:
            True if encryption succeeded, False otherwise
        """
        if not self._validate_input_file(file_to_encrypt):
            return False

        with self._password_context() as password:
            if not password:
                self.logger.error("Encryption aborted due to password issues")
                return False

            result = self._run_encryption_process(file_to_encrypt, password)
            if result:
                encrypted_file = f"{file_to_encrypt}.enc"
                self.logger.info("Encryption completed successfully!")
                self.logger.info(
                    "Encrypted file created: %s", Path(encrypted_file).name
                )
                self.logger.debug(
                    "Full path to encrypted file: %s", encrypted_file
                )
            else:
                self.logger.error(
                    "Encryption failed. Please check the logs for details."
                )
            return result

    def _run_encryption_process(
        self, file_to_encrypt: str, password: str
    ) -> bool:
        """Run encryption process with OpenSSL PBKDF2 parameters
        and embedded hash.

        Args:
            file_to_encrypt: Path to the file to encrypt
            password: Password for encryption

        Returns:
            True if encryption succeeded, False otherwise
        """
        # Calculate original hash
        file_name = Path(file_to_encrypt).name
        self.logger.info("Calculating SHA256 hash for file: %s", file_name)
        self.logger.debug("File path: %s", file_to_encrypt)
        original_hash = self._calculate_sha256(file_to_encrypt)
        self.logger.info("SHA256 hash calculated: %s", original_hash)
        self.logger.debug("SHA256 hash for %s: %s", file_name, original_hash)
        self.logger.info("Embedding integrity hash in encrypted file")

        # Create temp file with hash + original data
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as temp_file:
            # Write hash (64 bytes for SHA256 hex) + newline + original data
            hash_data = f"{original_hash}\n".encode()
            temp_file.write(hash_data)
            self.logger.debug(
                "Writing SHA256 hash to temp file: %s", original_hash
            )
            with Path(file_to_encrypt).open("rb") as orig:
                temp_file.write(orig.read())
            temp_path = temp_file.name

        output_path: str = f"{file_to_encrypt}.enc"
        cmd: list[str] = [
            "openssl",
            "enc",
            "-aes-256-cbc",
            "-a",
            "-salt",
            "-pbkdf2",
            "-iter",
            str(self.PBKDF2_ITERATIONS),
            "-in",
            temp_path,
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
            self.logger.debug(
                "Encryption success: %s", self._sanitize_logs(result.stderr)
            )
            return True
        except subprocess.CalledProcessError as e:
            self.logger.exception(
                "Encryption failed: %s", self._sanitize_logs(e.stderr)
            )
            self._safe_cleanup(output_path)
            return False
        except subprocess.TimeoutExpired:
            self.logger.exception("Encryption timed out")
            self._safe_cleanup(output_path)
            return False
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)
