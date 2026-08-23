"""Decrypt manager for handling decryption operations.

This module contains the DecryptManager class that encapsulates
the core decryption logic with retry, automatic integrity verification
using AES-256-GCM authenticated encryption, and SHA256 hash verification.
"""

from __future__ import annotations

import time
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from autotarcompress.base_manager import BaseCryptoManager
from autotarcompress.metadata import get_file_hash, update_decrypted_hash
from autotarcompress.utils import calculate_sha256


class DecryptManager(BaseCryptoManager):
    """Manager class for decryption operations.

    Handles the core decryption logic using AES-256-GCM authenticated
    decryption with password retry and automatic integrity verification.
    """

    MAX_PASSWORD_ATTEMPTS = 3
    BASE_BACKOFF_DELAY = 1.0
    MAX_BACKOFF_DELAY = 30.0
    MIN_ENCRYPTED_SIZE = 44  # salt(16) + nonce(12) + tag(16)

    def _validate_input_file(self, file_path: str) -> bool:
        """Validate the encrypted file before attempting decryption.

        Extends the base validation with a minimum-size check specific to
        encrypted files.  A valid encrypted file must contain at least:
          - 16 bytes of PBKDF2 salt
          - 12 bytes of AES-GCM nonce
          - 16 bytes of GCM authentication tag
        = 44 bytes minimum (MIN_ENCRYPTED_SIZE).

        Without this check, a truncated file passes the base empty-file
        check but then fails mid-decryption with a confusing internal error.

        Args:
            file_path: Path to the encrypted file to validate

        Returns:
            True if the file is valid for decryption, False otherwise
        """
        # call the parent class check first (file must exist, not empty)
        if not super()._validate_input_file(file_path):
            return False

        # additionally enforce minimum encrypted file size
        size = Path(file_path).stat().st_size
        if size < self.MIN_ENCRYPTED_SIZE:
            self.logger.error(
                "File is too small to be a valid encrypted archive "
                "(%d bytes; minimum expected is %d bytes). "
                "The file may be truncated or corrupted.",
                size,
                self.MIN_ENCRYPTED_SIZE,
            )
            return False

        return True

    def execute_decrypt(self, file_path: str) -> bool:
        """Execute the complete decryption process with retries.

        GCM mode automatically verifies integrity via authentication tag.

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
        decrypted_path = input_path.parent / f"{stem}-decrypted"

        self.logger.debug(
            "Decrypted output will be saved to: %s", str(decrypted_path)
        )

        attempt = 0
        while attempt < self.MAX_PASSWORD_ATTEMPTS:
            try:
                with self._password_context() as password:
                    if password is None:
                        return False

                    success = self._run_decryption_process(
                        file_path, password, str(decrypted_path)
                    )
                    if success:
                        # Calculate hash and verify integrity
                        self._verify_decrypted_integrity(
                            file_path, str(decrypted_path)
                        )

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

                    # Wrong password - retry with backoff
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
    ) -> bool:
        """Run streaming decryption with AES-256-GCM (chunked)."""

        CHUNK_SIZE = 64 * 1024  # must match encryption logic
        TAG_SIZE = 16
        NONCE_SIZE = self.NONCE_SIZE

        try:
            with (
                Path(file_path).open("rb") as fin,
                Path(decrypted_path).open("wb") as fout,
            ):
                salt = fin.read(self.SALT_SIZE)
                if len(salt) != self.SALT_SIZE:
                    self.logger.error(
                        "Invalid or corrupted encrypted file (salt missing)"
                    )
                    return False

                key = self._derive_key(password, salt)
                aesgcm = AESGCM(key)

                while True:
                    nonce = fin.read(NONCE_SIZE)
                    if not nonce:
                        break

                    if len(nonce) != NONCE_SIZE:
                        self.logger.error("Corrupted nonce block detected")
                        self._safe_cleanup(decrypted_path)
                        return False

                    # ciphertext + tag
                    chunk = fin.read(CHUNK_SIZE + TAG_SIZE)
                    if not chunk:
                        break

                    try:
                        plaintext = aesgcm.decrypt(nonce, chunk, None)
                    except InvalidTag:
                        self.logger.warning(
                            "Decryption failed: wrong password or tampered data"
                        )
                        self._safe_cleanup(decrypted_path)
                        return False

                    fout.write(plaintext)

            self.logger.info(
                "Decryption and integrity verification successful"
            )

        except Exception:
            self.logger.exception("Decryption failed with error")
            self._safe_cleanup(decrypted_path)
            return False

        else:
            return True

    def _verify_decrypted_integrity(
        self, encrypted_file: str, decrypted_path: str
    ) -> None:
        """Calculate hash of decrypted file and verify against backup.

        Args:
            encrypted_file: Path to the encrypted file
                (e.g., 06-01-2026.tar.zst.enc)
            decrypted_path: Path to the decrypted file
        """
        try:
            self.logger.info("Calculating SHA256 hash of decrypted file...")
            decrypted_hash = calculate_sha256(decrypted_path)
            self.logger.debug("Decrypted file hash: %s", decrypted_hash[:16])

            # Store the decrypted file hash
            update_decrypted_hash(
                Path(self.config.config_dir),
                Path(decrypted_path),
                decrypted_hash,
            )

            # Determine original backup filename from encrypted file
            # e.g., 06-01-2026.tar.zst.enc -> 06-01-2026.tar.zst
            encrypted_path = Path(encrypted_file)
            if encrypted_path.suffix == ".enc":
                backup_filename = encrypted_path.stem
            else:
                backup_filename = encrypted_path.name

            # Try to verify against original backup archive hash
            backup_hash = get_file_hash(
                Path(self.config.config_dir), backup_filename
            )

            if backup_hash:
                if decrypted_hash == backup_hash:
                    self.logger.info(
                        "✓ Integrity verification passed: "
                        "Decrypted file matches original backup (%s)",
                        backup_filename,
                    )
                else:
                    self.logger.warning(
                        "⚠ Integrity verification failed: "
                        "Decrypted file hash differs from backup archive (%s)",
                        backup_filename,
                    )
                    self.logger.warning(
                        "This may indicate corruption during "
                        "encryption/decryption"
                    )
                    self.logger.debug("Expected: %s", backup_hash)
                    self.logger.debug("Got: %s", decrypted_hash)
            else:
                self.logger.info(
                    "No hash found for backup archive %s", backup_filename
                )

        except OSError:
            self.logger.exception("Failed to verify decrypted file integrity")
