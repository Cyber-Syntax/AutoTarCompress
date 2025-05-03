import datetime
import getpass
import gettext
import hashlib
import itertools
import json
import logging
import os
import re
import subprocess
import sys
import tarfile
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from tqdm import tqdm

_ = gettext.gettext

# --------------------------
# Configuration Management
# --------------------------


@dataclass
class BackupConfig:
    """Configuration data for backup manager.

    This class handles configuration properties for the backup system including
    file paths, retention policies, and backup targets.
    """

    backup_folder: str = "~/Documents/backup-for-cloud/"
    config_dir: str = "~/.config/autotarcompress"
    keep_backup: int = 1
    keep_enc_backup: int = 1
    dirs_to_backup: List[str] = field(default_factory=list)
    ignore_list: List[str] = field(default_factory=list)
    last_backup: Optional[str] = None

    def __post_init__(self):
        """Expand all paths after initialization."""
        self.backup_folder = os.path.expanduser(self.backup_folder)
        self.ignore_list = [os.path.expanduser(p) for p in self.ignore_list]
        self.dirs_to_backup = [os.path.expanduser(d) for d in self.dirs_to_backup]
        self.config_dir = os.path.expanduser(self.config_dir)

    @property
    def current_date(self) -> str:
        """Get current date formatted as string."""
        return datetime.datetime.now().strftime("%d-%m-%Y")

    @property
    def config_path(self) -> str:
        """Get the full path to the config file."""
        return os.path.join(self.config_dir, "config.json")

    @property
    def backup_path(self) -> str:
        """Get the full path to the backup file."""
        return os.path.expanduser(f"{self.backup_folder}/{self.current_date}.tar.xz")

    def save(self) -> None:
        """Save current configuration to the config file."""
        config_data = {
            "backup_folder": self.backup_folder,
            "config_dir": self.config_dir,
            "keep_backup": self.keep_backup,
            "keep_enc_backup": self.keep_enc_backup,
            "dirs_to_backup": self.dirs_to_backup,
            "ignore_list": self.ignore_list,
            "last_backup": self.last_backup,
        }

        # Ensure the config directory exists
        os.makedirs(self.config_dir, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump(config_data, f, indent=4)

        logging.info(f"Configuration saved to {self.config_path}")

    @classmethod
    def load(cls) -> "BackupConfig":
        """Load configuration from file or create with defaults if not exists."""
        default_config = cls()
        config_path = default_config.config_path

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config_data = json.load(f)
                return cls(**config_data)
            except json.JSONDecodeError as e:
                logging.error(f"Error reading config file: {e}")
                logging.warning("Using default configuration")
                return default_config
        return default_config

    @classmethod
    def verify_config(cls) -> Tuple[bool, str]:
        """Verify if the configuration file exists and is properly set up.

        Returns:
            Tuple containing:
            - bool: True if configuration is valid, False otherwise
            - str: Message describing the verification result
        """
        default_config = cls()
        config_path = default_config.config_path

        # Check if config file exists
        if not os.path.exists(config_path):
            return False, f"Configuration file not found at {config_path}"

        try:
            # Try to load the configuration
            with open(config_path, "r") as f:
                config_data = json.load(f)

            config = cls(**config_data)

            # Validate essential configuration
            if not config.dirs_to_backup:
                return False, "No backup directories configured"

            # Check if backup folder exists or can be created
            backup_folder = os.path.expanduser(config.backup_folder)
            if not os.path.exists(backup_folder):
                try:
                    os.makedirs(backup_folder, exist_ok=True)
                except OSError:
                    return False, f"Cannot create backup folder at {backup_folder}"

            # All checks passed
            return True, "Configuration is valid"

        except json.JSONDecodeError:
            return False, "Configuration file is corrupt or invalid JSON"
        except KeyError as e:
            return False, f"Missing required configuration key: {e}"
        except Exception as e:
            return False, f"Configuration validation error: {str(e)}"

# --------------------------
# Command Pattern
# --------------------------


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


# TODO: Add decrypted file path too
# add prints for user to see the progress
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


# --------------------------
# Support Components
# --------------------------


class SizeCalculator:
    """Calculate total size of directories to be backed up and display results."""

    def __init__(self, directories: List[str], ignore_list: List[str]):
        # Expand user paths (e.g., ~) and normalize the directories and ignore list.
        self.directories = [os.path.expanduser(d) for d in directories]
        self.ignore_list = [os.path.expanduser(p) for p in ignore_list]

    def calculate_total_size(self) -> int:
        """
        Iterate over all directories and sum up their sizes.

        Returns:
            Total size in bytes.
        """
        print("\n📂 **Backup Size Summary**")
        print("=" * 40)

        total = 0
        for directory in self.directories:
            dir_size = self._calculate_directory_size(directory)
            total += dir_size
            print(f"📁 {directory}: {self._format_size(dir_size)}")

        print("=" * 40)
        print(f"✅ Total Backup Size: {self._format_size(total)}\n")
        return total

    def _calculate_directory_size(self, directory: str) -> int:
        """
        Calculate the size of a directory recursively.

        Args:
            directory (str): The path of the directory to calculate size.

        Returns:
            The total size in bytes of files within the directory.
        """
        total = 0
        try:
            # Walk the directory tree.
            for root, dirs, files in os.walk(directory):
                if self._should_ignore(root):
                    dirs[:] = []  # Prevent descending into subdirectories.
                    continue

                for f in files:
                    file_path = os.path.join(root, f)
                    if self._should_ignore(file_path):
                        continue
                    try:
                        total += os.path.getsize(file_path)
                    except OSError as e:
                        logging.warning(f"⚠️ Error accessing file {file_path}: {e}")
        except Exception as e:
            logging.warning(f"⚠️ Error accessing directory {directory}: {e}")
        return total

    def _should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored."""
        return any(ignore in path for ignore in self.ignore_list)

    def _format_size(self, size_in_bytes: int) -> str:
        """
        Convert a size in bytes to a human-readable format (KB, MB, GB).

        Args:
            size_in_bytes (int): The size in bytes.

        Returns:
            str: The formatted size string.
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} PB"

    def _should_ignore(self, path: str) -> bool:
        """
        Determine whether the given path should be ignored based on the ignore list.

        The check is performed using the normalized path to avoid mismatches due to path formatting.

        Args:
            path (str): The file or directory path to check.

        Returns:
            True if the path starts with any of the ignore paths, False otherwise.
        """
        # Normalize the path for a consistent comparison.
        normalized_path = os.path.normpath(path)
        return any(
            normalized_path.startswith(os.path.normpath(ignored)) for ignored in self.ignore_list
        )


# --------------------------
# Facade
# --------------------------


class BackupFacade:
    """Facade to manage backup manager operations"""

    def __init__(self):
        self.config = BackupConfig.load()
        self.commands: Dict[str, Command] = {
            "backup": BackupCommand(self.config),
            "cleanup": CleanupCommand(self.config),
        }

    def configure(self):
        """Interactive configuration wizard"""
        print("\n=== Backup Manager Configuration ===")
        self._setup_paths()
        self._setup_retention()
        self._setup_directories()
        self.config.save()
        print("\nConfiguration saved successfully!")

    def execute_command(self, command_name: str):
        """Execute a predefined command"""
        if command_name in self.commands:
            self.commands[command_name].execute()
        else:
            raise ValueError(f"Unknown command: {command_name}")

    def _setup_paths(self):
        """Configure backup storage location"""
        print("\n=== Backup Storage Location ===")
        new_path = input(
            "Enter backup directory (default: ~/Documents/backup-for-cloud/): "
        ).strip()
        if new_path:
            self.config.backup_folder = new_path
        print(f"Using backup directory: {os.path.expanduser(self.config.backup_folder)}")

    def _setup_retention(self):
        """Configure backup retention policies"""
        print("\n=== Backup Retention Settings ===")
        try:
            self.config.keep_backup = int(
                input("Number of regular backups to keep (default 1): ") or self.config.keep_backup
            )
            self.config.keep_enc_backup = int(
                input("Number of encrypted backups to keep (default 1): ")
                or self.config.keep_enc_backup
            )
        except ValueError:
            print("Invalid number format. Using existing values.")

    def _setup_directories(self):
        """Interactive directory configuration"""
        print("\n=== Directory Configuration ===")
        self._manage_path_list(
            "Backup Directories",
            self.config.dirs_to_backup,
            "Enter directories to add (comma-separated): ",
            "Current backup directories:",
        )
        self._manage_path_list(
            "Ignored Paths",
            self.config.ignore_list,
            "Enter paths to ignore (comma-separated): ",
            "Current ignored paths:",
        )

    def _manage_path_list(self, title: str, target_list: list, add_prompt: str, list_header: str):
        """Generic interactive list manager"""
        while True:
            print(f"\n{list_header}")
            if not target_list:
                print("  None configured")
            else:
                for i, path in enumerate(target_list, 1):
                    expanded = os.path.expanduser(path)
                    status = "(exists)" if os.path.exists(expanded) else "(not found)"
                    print(f"  {i}. {path} {status}")

            print("\nOptions:")
            print("1. Add paths")
            print("2. Remove path")
            print("3. Finish configuration")

            try:
                choice = int(input("Choose an option (1-3): "))
            except ValueError:
                print("Please enter a valid number")
                continue

            if choice == 1:
                new_items = input(add_prompt).split(",")
                cleaned_paths = self._validate_paths([p.strip() for p in new_items])
                target_list.extend(p for p in cleaned_paths if p not in target_list)
            elif choice == 2:
                self._remove_path(target_list)
            elif choice == 3:
                break
            else:
                print("Invalid choice. Please try again.")

    def _validate_paths(self, paths: List[str]) -> List[str]:
        """Validate and normalize paths with user confirmation"""
        valid_paths = []
        for path in paths:
            if not path:
                continue

            expanded = os.path.expanduser(path)
            if not os.path.exists(expanded):
                print(f"Warning: Path does not exist - {expanded}")
                if input("Add anyway? (y/N): ").lower() != "y":
                    continue

            # Store original path with ~ if provided
            valid_paths.append(path)
        return valid_paths

    def _remove_path(self, target_list: list):
        """Safely remove items from list"""
        if not target_list:
            print("List is empty")
            return

        try:
            index = int(input(f"Enter number to remove (1-{len(target_list)}): ")) - 1
            if 0 <= index < len(target_list):
                removed = target_list.pop(index)
                print(f"Removed: {removed}")
            else:
                print("Invalid index number")
        except ValueError:
            print("Please enter a valid number")


# HACK: Use ContextManager class to pass _password_context and _safe_cleanup methods
# NOTE: Python’s garbage collector or internal caching might still have copies elsewhere??


# TODO: mmap or mlock, cryptography, or C extension for better memory handling
# TODO: ctypes(mlock) better for this scenario?
# cryptography is much better but it's complex to use (consider for future)
class ContextManager:
    """Secure context manager for password handling"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def _password_context(self):
        """Secure password handling with proper memory sanitization.
        By using mutable object like bytearray you can overwrite the data in memory
        """
        try:
            # Get inmutable password from user
            password = getpass.getpass("Enter file encryption password: ")
            if not password:
                self.logger.error("Empty password rejected")
                yield None
                return

            # Convert to mutable bytearray for secure cleanup
            password_bytes = bytearray(password.encode("utf-8"))
            yield password_bytes.decode("utf-8")

        finally:
            # Securely overwrite the memory
            if "password_bytes" in locals():
                # Overwrite each byte with zero
                for i in range(len(password_bytes)):
                    password_bytes[i] = 0
                # Prevent compiler optimizations from skipping the loop
                password_bytes = None
                del password_bytes

    def _safe_cleanup(self, path: str):
        """Securely remove partial files on failure"""
        try:
            if os.path.exists(path):
                os.remove(path)
                self.logger.info("Cleaned up partial encrypted file")
        except Exception as e:
            self.logger.error(f"Failed to clean up {path}: {str(e)}")


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
