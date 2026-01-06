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
from autotarcompress.utils.hash_utils import calculate_sha256


class DecryptManager(BaseCryptoManager):
    """Manager class for decryption operations.

    Handles the core decryption logic using AES-256-GCM authenticated
    decryption with password retry and automatic integrity verification.
    """

    MAX_PASSWORD_ATTEMPTS = 3
    BASE_BACKOFF_DELAY = 1.0
    MAX_BACKOFF_DELAY = 30.0
    MIN_ENCRYPTED_SIZE = 44  # salt(16) + nonce(12) + tag(16)

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
        """Run decryption with AES-256-GCM.

        File format: [salt(16)][nonce(12)][ciphertext][tag(16)]

        Args:
            file_path: Path to the encrypted file
            password: Password for decryption
            decrypted_path: Path for the decrypted output

        Returns:
            True if decryption succeeded, False if wrong password or tampered
        """
        try:
            # Read encrypted file
            with Path(file_path).open("rb") as f:
                encrypted_data = f.read()

            # Validate minimum encrypted file size
            if len(encrypted_data) < self.MIN_ENCRYPTED_SIZE:
                self.logger.error("Encrypted file is too small or corrupted")
                return False

            # Extract components
            salt = encrypted_data[: self.SALT_SIZE]
            nonce = encrypted_data[
                self.SALT_SIZE : self.SALT_SIZE + self.NONCE_SIZE
            ]
            ciphertext_with_tag = encrypted_data[
                self.SALT_SIZE + self.NONCE_SIZE :
            ]

            self.logger.debug("Extracted salt and nonce from encrypted file")

            # Derive key from password
            key = self._derive_key(password, salt)
            self.logger.debug("Derived decryption key using PBKDF2")

            # Decrypt and verify with AES-GCM
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)

            # Write decrypted data
            with Path(decrypted_path).open("wb") as f:
                f.write(plaintext)

            self.logger.info(
                "Decryption and integrity verification successful"
            )
            self.logger.debug(
                "Decrypted %d bytes to %d bytes",
                len(ciphertext_with_tag),
                len(plaintext),
            )

        except InvalidTag:
            # Wrong password or tampered data
            self.logger.warning(
                "Decryption failed: wrong password or file has been tampered"
            )
            self._safe_cleanup(decrypted_path)
            return False

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

        except (FileNotFoundError, OSError):
            self.logger.exception("Failed to verify decrypted file integrity")
