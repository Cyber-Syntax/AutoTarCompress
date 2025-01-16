import os
import subprocess
import sys
import time
import getpass
import logging
import hashlib
from typing import List
from dataclasses import dataclass, field
from .config import Config
from .utils import list_backup_files, select_file


@dataclass
class EncryptionManager:
    decrypt_file_path: str = field(init=False)
    config: Config

    def __post_init__(self):
        self.decrypt_file_path = os.path.join(
            os.path.expanduser(self.config.backup_folder), "decrypted.tar.xz"
        )

    def encrypt_backup(self) -> bool:
        """Encrypt a selected backup file with openssl."""
        try:
            # Select a `.tar.xz` file to encrypt
            file_to_encrypt = select_file(extension=".tar.xz")
            password = getpass.getpass(prompt="Enter encryption password: ")

            # Define encrypted file path
            encrypted_file = f"{file_to_encrypt}.enc"

            encrypt_cmd = [
                "openssl",
                "aes-256-cbc",
                "-a",
                "-salt",
                "-pbkdf2",
                "-in",
                file_to_encrypt,
                "-out",
                encrypted_file,
                "-pass",
                f"pass:{password}",
            ]

            # Run the encryption command
            subprocess.run(encrypt_cmd, check=True)
            logging.info(f"Encryption completed successfully: {encrypted_file}")
            return True
        except ValueError as e:
            logging.error(f"Encryption failed: {e}")
            return False
        except subprocess.CalledProcessError as error:
            logging.error(f"Error encrypting file: {error}")
            return False
        except KeyboardInterrupt:
            logging.info("Encryption cancelled.")
            sys.exit(0)

    def decrypt_file(self, file_to_decrypt: str, password: str) -> bool:
        """Decrypt the selected file using OpenSSL."""
        decrypt_cmd = [
            "openssl",
            "aes-256-cbc",
            "-d",
            "-a",
            "-salt",
            "-pbkdf2",
            "-in",
            file_to_decrypt,
            "-out",
            self.decrypt_file_path,
            "-pass",
            f"pass:{password}",
        ]

        try:
            # Run the decryption command
            subprocess.run(decrypt_cmd, check=True)
            logging.info(f"Decryption completed successfully: {self.decrypt_file_path}")
            return True
        except subprocess.CalledProcessError as error:
            logging.error(f"Error decrypting file: {error}")
            return False
        except KeyboardInterrupt:
            logging.info("Decryption cancelled.")
            raise

    def verify_decrypt_file(self, original_file_path: str) -> None:
        """Verify the decrypted file's integrity by comparing checksums."""
        actual_checksum = self.compute_checksum(self.decrypt_file_path)
        expected_checksum = self.compute_checksum(original_file_path)

        if actual_checksum == expected_checksum:
            logging.info("File integrity verified: checksums match.")
        else:
            logging.error("File integrity check failed: checksums do not match.")

    @staticmethod
    def compute_checksum(file_path: str) -> str:
        """Compute the SHA256 checksum of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def decrypt(self) -> bool:
        """Main decryption workflow."""
        try:
            # Select a `.enc` file to decrypt
            file_to_decrypt = select_file(extension=".enc")
            password = getpass.getpass(prompt="Enter decryption password: ")

            if self.decrypt_file(file_to_decrypt, password):
                # Verify integrity by comparing with the original file
                original_file_path = file_to_decrypt.replace(".enc", "")
                self.verify_decrypt_file(original_file_path)
                return True
        except ValueError as e:
            logging.error(f"Decryption failed: {e}")
            return False
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return False
