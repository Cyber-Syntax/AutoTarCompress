import os
import subprocess
import sys
import time
import getpass
import logging
import hashlib
from dataclasses import dataclass, field
from .config import Config
import utils


@dataclass
class EncryptionManager:
    decrypt_file_path: str = field(init=False)
    config: Config

    def __post_init__(self):
        self.decrypt_file_path = os.path.join(
            os.path.expanduser(self.config.backup_folder), f"decrypted.tar.xz"
        )

    def encrypt_backup(self) -> bool:
        """Encrypt the backup file with openssl command"""
        password = getpass.getpass(prompt="Enter encryption password: ")
        current_date = self.config.current_date

        # The encrypted backup file will be named with the current date
        file_to_encrypt = os.path.join(
            os.path.expanduser(self.config.backup_folder), f"{current_date}.tar.xz.enc"
        )

        # Encrypt the backed up file with openssl command
        encrypt_cmd = [
            "openssl",
            "aes-256-cbc",
            "-a",
            "-salt",
            "-pbkdf2",
            "-in",
            self.config.backup_file_path,
            "-out",
            file_to_encrypt,
            "-pass",
            f"pass:{password}",
        ]

        try:
            subprocess.run(encrypt_cmd, check=True)
            logging.info("Encryption completed successfully")
            return True
        except subprocess.CalledProcessError as error:
            logging.error(f"Error encrypting file: {error}")
            return False
        except KeyboardInterrupt:
            logging.info("Encryption cancelled")
            sys.exit(0)

    def decrypt(self, file_to_decrypt: str) -> bool:
        """Decrypt the backup file"""
        password = getpass.getpass(prompt="Enter decryption password: ")

        # List all encrypted files
        print("=====================================")
        print("Choose which file to decrypt: ")
        # List only encrypted files
        files = utils.list_backup_files(extension=".enc")

        if not files:
            return False

        choice = int(input("Enter your choice: "))

        # files[choice - 1] -> get file name from list files
        file_to_decrypt = os.path.join(
            os.path.expanduser(self.config.backup_folder), files[choice - 1]
        )

        # Decrypt the backup file with openssl command
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
            subprocess.run(decrypt_cmd, check=True)
            time.sleep(1)
            logging.info("Decryption completed successfully")
            return True
        except subprocess.CalledProcessError as error:
            logging.error(f"Error decrypting file: {error}")
            return False
        except KeyboardInterrupt:
            logging.info("Decryption cancelled")
            sys.exit(0)

    def verify_decrypt_file(self, file_to_decrypt: str):
        """Verify the decrypted file is the same as the original file"""
        original_file_path = file_to_decrypt[:-4]

        # Compute the SHA256 checksum of the decrypted file
        hasher = hashlib.sha256()
        with open(self.decrypt_file_path, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                hasher.update(data)
        actual_checksum = hasher.hexdigest()

        # Compute the SHA256 checksum of the original file
        hasher_original = hashlib.sha256()
        with open(original_file_path, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                hasher_original.update(data)
        expected_checksum = hasher_original.hexdigest()

        # Compare the checksums
        if actual_checksum == expected_checksum:
            logging.info("File integrity verified: checksums match")
        else:
            logging.error("File integrity check failed: checksums do not match")
