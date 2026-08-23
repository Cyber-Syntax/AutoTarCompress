"""Encrypt manager for handling encryption operations.

This module contains the EncryptManager class that encapsulates
the core encryption logic using AES-256-GCM authenticated encryption
with SHA256 integrity verification.
"""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from autotarcompress.base_manager import BaseCryptoManager
from autotarcompress.metadata import update_encrypted_hash
from autotarcompress.utils import calculate_sha256


class EncryptManager(BaseCryptoManager):
    """Manager class for encryption operations.

    Handles the core encryption logic using AES-256-GCM authenticated
    encryption with PBKDF2-HMAC-SHA256 key derivation.
    """

    def execute_encrypt(self, file_to_encrypt: str) -> bool:
        """Execute the complete encryption process with AES-GCM.

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
                self._calculate_and_store_hash(encrypted_file)
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

    def _calculate_and_store_hash(self, encrypted_file: str) -> None:
        """Calculate SHA256 hash of encrypted file and store in metadata.

        Args:
            encrypted_file: Path to the encrypted file
        """
        try:
            self.logger.info("Calculating SHA256 hash of encrypted file...")
            encrypted_hash = calculate_sha256(encrypted_file)
            self.logger.debug("Encrypted file hash: %s", encrypted_hash[:16])

            update_encrypted_hash(
                Path(self.config.config_dir),
                Path(encrypted_file),
                encrypted_hash,
            )
        except OSError:
            self.logger.exception("Failed to calculate encrypted file hash")

    def _run_encryption_process(
        self, file_to_encrypt: str, password: str
    ) -> bool:
        """Run streaming encryption with AES-256-GCM (chunked).

        Reads the input file in 64 KB chunks.  Each chunk gets its own
        random nonce and is encrypted independently.  The salt is written
        once at the start of the output file; each chunk is preceded by
        its nonce.

        File layout on disk:
            [16-byte salt][12-byte nonce][ciphertext+16-byte tag] × N chunks

        Args:
            file_to_encrypt: Path to the plaintext file
            password: The user's password (will be key-derived with PBKDF2)

        Returns:
            True if encryption succeeded, False otherwise
        """
        CHUNK_SIZE = 64 * 1024  # 64 KB per chunk

        file_name = Path(file_to_encrypt).name
        self.logger.info("Encrypting file with AES-256-GCM: %s", file_name)

        output_path = f"{file_to_encrypt}.enc"

        try:
            salt = self._generate_salt()
            key = self._derive_key(password, salt)

            self.logger.debug("Generated salt and derived key")

            with (
                Path(file_to_encrypt).open("rb") as fin,
                Path(output_path).open("wb") as fout,
            ):
                fout.write(salt)

                aesgcm = AESGCM(key)

                while True:
                    plaintext_chunk = fin.read(CHUNK_SIZE)
                    if not plaintext_chunk:
                        break

                    nonce = self._generate_nonce()
                    ciphertext = aesgcm.encrypt(nonce, plaintext_chunk, None)

                    fout.write(nonce)
                    fout.write(ciphertext)

            self.logger.info("Encryption successful with streaming AES-GCM")

        except (OSError, ValueError):
            self.logger.exception("Encryption failed with error")
            self._safe_cleanup(output_path)
            return False

        else:
            return True
