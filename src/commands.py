"""Command pattern implementations for backup operations.

This module contains the Command interface and concrete command implementations
for backup, encryption, decryption, extraction, and cleanup operations.
"""

import hashlib
import itertools
import logging
import os
import re
import subprocess
import sys
import tarfile
import time
from abc import ABC, abstractmethod
from typing import List

from src.config import BackupConfig
from src.security import ContextManager
from src.utils import SizeCalculator


class Command(ABC):
    """Command interface for backup manager"""

    @abstractmethod
    def execute(self):
        pass


class BackupCommand(Command):
    """Concrete command to perform backup"""

    def __init__(self, config: BackupConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def execute(self):
        """Execute backup process"""
        if not self.config.dirs_to_backup:
            self.logger.error("No directories configured for backup")
            return False

        total_size = self._calculate_total_size()
        self._run_backup_process(total_size)
        return True

    def _calculate_total_size(self) -> int:
        calculator = SizeCalculator(self.config.dirs_to_backup, self.config.ignore_list)
        return calculator.calculate_total_size()

    # HACK: use loading spinner as a workaround loading which tqdm won't work

    def _run_backup_process(self, total_size: int):
        # Check is there any file exist with same name
        if os.path.exists(self.config.backup_path):
            print(f"File already exist: {self.config.backup_path}")
            if input("Do you want to remove it? (y/n): ").lower() == "y":
                os.remove(self.config.backup_path)
            else:
                return

        exclude_options = " ".join([f"--exclude={path}" for path in self.config.ignore_list])

        # TODO: need to fix this exclude option
        # TEST: without os.path.basename which it is not working
        # exclude_options += f" --exclude={self.config.backup_folder}"

        dir_paths = [os.path.expanduser(path) for path in self.config.dirs_to_backup]
        # HACK: h option is used to follow symlinks
        cmd = (
            f"tar -chf - --one-file-system {exclude_options} {' '.join(dir_paths)} | "
            f"xz --threads={os.cpu_count() - 1} > {self.config.backup_path}"
        )
        total_size_gb = total_size / 1024**3

        self.logger.info(f"Starting backup to {self.config.backup_path}")
        self.logger.info(f"Total size: {total_size_gb} GB")

        try:
            # FIX: later spinner not working for now
            # FAILED: not work as expected because of "| tar: Removing leading `/' from member names" outputs
            # self._show_spinner(subprocess.Popen(cmd, shell=True))
            subprocess.run(cmd, shell=True, check=True)
            self.logger.info("Backup completed successfully")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Backup failed: {e}")

    def _show_spinner(self, process):
        spinner = itertools.cycle(["/", "-", "\\", "|"])
        while process.poll() is None:
            sys.stdout.write(next(spinner) + " ")
            sys.stdout.flush()
            sys.stdout.write("\b\b")
            time.sleep(0.1)


# TESTING: increasing security with fd0 and iterations
# TEST: Is it realy delete password from memory?
# Is it better way to handle this?


# TODO: add a key file option with master password for better security
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

        self.required_openssl_version = (3, 0, 0)  # Argon2id requires OpenSSL 3.0+

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

    def _sanitize_logs(self, output: bytes) -> str:
        """Safe log sanitization without modifying bytes"""
        sanitized = output.replace(b"password=", b"password=[REDACTED]")
        sanitized = re.sub(rb"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", b"[IP_REDACTED]", sanitized)
        return sanitized.decode("utf-8", errors="replace")


class DecryptCommand(Command):
    PBKDF2_ITERATIONS = 600000  # Must match encryption iterations

    def __init__(self, config, file_path):
        self.config = config
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)
        self._password_context = ContextManager()._password_context
        self._safe_cleanup = ContextManager()._safe_cleanup

    def execute(self):
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
                self._verify_integrity(output_path)
                return True
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Decryption failed: {self._sanitize_logs(e.stderr)}")
                self._safe_cleanup(output_path)
                return False

    def _verify_integrity(self, decrypted_path: str):
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


class CleanupCommand(Command):
    """Concrete command to perform cleanup of old backups"""

    def __init__(self, config: BackupConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def execute(self):
        self._cleanup_files(".tar.xz", self.config.keep_backup)
        self._cleanup_files(".tar.xz.enc", self.config.keep_enc_backup)

    def _cleanup_files(self, ext: str, keep_count: int):
        files = sorted(
            [f for f in os.listdir(self.config.backup_folder) if f.endswith(ext)],
            key=lambda x: datetime.datetime.strptime(x.split(".")[0], "%d-%m-%Y"),
        )

        for old_file in files[:-keep_count]:
            try:
                os.remove(os.path.join(self.config.backup_folder, old_file))
                self.logger.info(f"Deleted old backup: {old_file}")
                print(f"Deleted old backup: {old_file}")
            except Exception as e:
                self.logger.error(f"Failed to delete {old_file}: {e}")


class ExtractCommand(Command):
    def __init__(self, config, file_path):
        self.config = config
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)

    def execute(self):
        extract_dir = f"{os.path.splitext(self.file_path)[0]}-extracted"
        os.makedirs(extract_dir, exist_ok=True)

        try:
            with tarfile.open(self.file_path, "r:xz") as tar:
                tar.extractall(path=extract_dir)
            self.logger.info(f"Successfully extracted to {extract_dir}")
            return True
        except tarfile.TarError as e:
            self.logger.error(f"Extraction failed: {e}")
            return False
