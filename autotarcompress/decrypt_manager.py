"""Decrypt manager for handling decryption operations.

This module contains the DecryptManager class that encapsulates
the core decryption logic with retry and integrity verification.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

from autotarcompress.base_manager import BaseCryptoManager


class DecryptManager(BaseCryptoManager):
    """Manager class for decryption operations.

    Handles the core decryption logic including password retry with backoff,
    OpenSSL operations, and mandatory integrity verification.
    """

    MAX_PASSWORD_ATTEMPTS = 3
    BASE_BACKOFF_DELAY = 1.0
    MAX_BACKOFF_DELAY = 30.0

    def execute_decrypt(self, file_path: str) -> bool:
        """Execute the complete decryption process with retries and integrity check.

        Args:
            file_path: Path to the encrypted file to decrypt

        Returns:
            True if decryption and integrity check succeed, False otherwise
        """
        self.logger.info(
            "Starting decryption of file: %s", Path(file_path).name
        )
        self.logger.debug("Full path to encrypted file: %s", file_path)

        if not self._validate_input_file(file_path):
            return False

        input_path = Path(file_path)
        stem = input_path.stem
        original_path = input_path.parent / stem
        decrypted_path = input_path.parent / f"{stem}-decrypted"

        self.logger.debug(
            "Decrypted output will be saved to: %s", str(decrypted_path)
        )
        self.logger.debug(
            "Original file path for integrity check: %s", str(original_path)
        )

        attempt = 0
        while attempt < self.MAX_PASSWORD_ATTEMPTS:
            try:
                with self._password_context() as password:
                    if password is None:
                        return False

                    success, extracted_hash = self._run_decryption_process(
                        file_path, password, str(decrypted_path)
                    )
                    if success:
                        # Mandatory integrity check
                        if not self._verify_integrity_mandatory(
                            str(decrypted_path),
                            str(original_path),
                            extracted_hash,
                        ):
                            self._safe_cleanup(str(decrypted_path))
                            return False
                        self.logger.info("Decryption completed successfully!")
                        self.logger.info(
                            "Decrypted file saved as: %s",
                            Path(decrypted_path).name,
                        )
                        self.logger.debug(
                            "Full path to decrypted file: %s",
                            str(decrypted_path),
                        )
                        return True
                    # Wrong password or corrupted file
                    attempt += 1
                    if attempt < self.MAX_PASSWORD_ATTEMPTS:
                        delay = min(
                            self.BASE_BACKOFF_DELAY * (2**attempt),
                            self.MAX_BACKOFF_DELAY,
                        )
                        self.logger.warning(
                            "Decryption failed (attempt %d/%d). "
                            "Retrying in %.1fs...",
                            attempt,
                            self.MAX_PASSWORD_ATTEMPTS,
                            delay,
                        )
                        time.sleep(delay)
                    else:
                        self.logger.error("Maximum password attempts exceeded")
                        return False

            except Exception:
                self.logger.exception("Decryption error")
                return False

        return False

    def _run_decryption_process(
        self, file_path: str, password: str, decrypted_path: str
    ) -> tuple[bool, str]:
        """Run decryption and return (success, extracted_hash).

        Args:
            file_path: Path to the encrypted file
            password: Password for decryption
            decrypted_path: Path for the decrypted output

        Returns:
            Tuple of (success, extracted_hash)
        """
        # Decrypt to temp file first
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as temp_file:
            temp_decrypt_path = temp_file.name

        cmd: list[str] = [
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
            file_path,
            "-out",
            temp_decrypt_path,
            "-pass",
            "fd:0",
        ]

        try:
            subprocess.run(
                cmd,
                input=f"{password}\n".encode(),
                check=True,
                stderr=subprocess.PIPE,
                timeout=600,
                shell=False,
            )

            # Read hash from first line
            with Path(temp_decrypt_path).open("rb") as f:
                hash_line = f.readline().decode().strip()
                self.logger.debug(
                    "Extracted SHA256 hash from encrypted file: %s", hash_line
                )
                # Write remaining data to final decrypted path
                with Path(decrypted_path).open("wb") as out:
                    out.write(f.read())

            return True, hash_line
        except subprocess.CalledProcessError:
            return False, ""
        finally:
            # Clean up temp file
            Path(temp_decrypt_path).unlink(missing_ok=True)

    def _verify_integrity_mandatory(
        self, decrypted_path: str, original_path: str, fallback_hash: str
    ) -> bool:
        """Verify decrypted file against original backup file or embedded hash.

        Args:
            decrypted_path: Path to the decrypted file
            original_path: Path to the original backup file
            fallback_hash: Embedded hash as fallback

        Returns:
            True if check passes, False on mismatch
        """
        file_name = Path(decrypted_path).name
        original_name = Path(original_path).name
        self.logger.info(
            "Verifying integrity by comparing decrypted file '%s' "
            "with original file '%s'",
            file_name,
            original_name,
        )
        self.logger.debug("Decrypted file path: %s", decrypted_path)
        self.logger.debug("Original file path: %s", original_path)

        if Path(original_path).exists():
            # Check against original file
            original_hash = self._calculate_sha256(original_path)
            actual_hash = self._calculate_sha256(decrypted_path)
            self.logger.info("Original file SHA256: %s", original_hash)
            self.logger.info("Decrypted file SHA256: %s", actual_hash)

            if actual_hash != original_hash:
                self.logger.error(
                    "Integrity check failed: decrypted file '%s' hash %s "
                    "does not match original file '%s' hash %s",
                    file_name,
                    actual_hash,
                    original_name,
                    original_hash,
                )
                return False

            self.logger.info(
                "Integrity verification successful: decrypted file matches "
                "original file '%s'",
                original_name,
            )
        else:
            # Fallback to embedded hash
            self.logger.warning(
                "Original file '%s' not found, using embedded hash for verification",
                original_path,
            )
            actual_hash = self._calculate_sha256(decrypted_path)
            self.logger.info("Embedded hash: %s", fallback_hash)
            self.logger.info("Decrypted file SHA256: %s", actual_hash)

            if actual_hash != fallback_hash:
                self.logger.error(
                    "Integrity check failed: decrypted file '%s' hash %s "
                    "does not match embedded hash %s",
                    file_name,
                    actual_hash,
                    fallback_hash,
                )
                return False

            self.logger.info(
                "Integrity verification successful using embedded hash"
            )

        return True
