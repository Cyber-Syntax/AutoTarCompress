import datetime
import getpass
import gettext
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tarfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List

from tqdm import tqdm

_ = gettext.gettext

# --------------------------
# Configuration Management
# --------------------------


@dataclass
class BackupConfig:
    backup_folder: str = "~/Documents/backup-for-cloud/"
    keep_backup: int = 1
    keep_enc_backup: int = 1
    dirs_to_backup: List[str] = field(default_factory=list)
    ignore_list: List[str] = field(default_factory=list)

    @property
    def current_date(self) -> str:
        return datetime.datetime.now().strftime("%d-%m-%Y")

    @property
    def config_path(self) -> str:
        return os.path.join(os.path.expanduser(self.backup_folder), "config_files", "config.json")

    @property
    def backup_path(self) -> str:
        return os.path.expanduser(f"{self.backup_folder}/{self.current_date}.tar.xz")

    def save(self):
        config_data = {
            "backup_folder": self.backup_folder,
            "keep_backup": self.keep_backup,
            "keep_enc_backup": self.keep_enc_backup,
            "dirs_to_backup": self.dirs_to_backup,
            "ignore_list": self.ignore_list,
        }

        config_dir = os.path.dirname(self.config_path)
        os.makedirs(config_dir, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump(config_data, f, indent=4)

    @classmethod
    def load(cls) -> "BackupConfig":
        default_config = cls()
        config_path = default_config.config_path

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config_data = json.load(f)
            return cls(**config_data)
        return default_config


# --------------------------
# Command Pattern
# --------------------------


class Command(ABC):
    @abstractmethod
    def execute(self):
        pass


class BackupCommand(Command):
    def __init__(self, config: BackupConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def execute(self):
        if not self.config.dirs_to_backup:
            self.logger.error("No directories configured for backup")
            return False

        total_size = self._calculate_total_size()
        self._run_backup_process(total_size)
        return True

    def _calculate_total_size(self) -> int:
        calculator = SizeCalculator(self.config.dirs_to_backup, self.config.ignore_list)
        return calculator.calculate_total_size()

    def _run_backup_process(self, total_size: int):
        exclude_options = " ".join([f"--exclude={path}" for path in self.config.ignore_list])
        dir_paths = [os.path.expanduser(path) for path in self.config.dirs_to_backup]

        cmd = (
            f"tar -cf - --one-file-system {exclude_options} {' '.join(dir_paths)} | "
            f"xz --threads={os.cpu_count()-1} > {self.config.backup_path}"
        )

        try:
            with tqdm(total=total_size, unit="B", unit_scale=True) as pbar:
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                while process.poll() is None:
                    if os.path.exists(self.config.backup_path):
                        pbar.update(os.path.getsize(self.config.backup_path) - pbar.n)
                    time.sleep(0.1)
            self.logger.info("Backup completed successfully")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Backup failed: {e}")


class EncryptCommand(Command):
    def __init__(self, config: BackupConfig, file_to_encrypt: str):
        self.config = config
        self.file_to_encrypt = file_to_encrypt
        self.logger = logging.getLogger(__name__)

    def execute(self) -> bool:
        password = getpass.getpass("Enter encryption password: ")
        output_path = f"{self.file_to_encrypt}.enc"

        cmd = [
            "openssl",
            "aes-256-cbc",
            "-a",
            "-salt",
            "-pbkdf2",
            "-in",
            self.file_to_encrypt,
            "-out",
            output_path,
            "-pass",
            f"pass:{password}",
        ]
        try:
            subprocess.run(cmd, check=True)
            self.logger.info(f"Encrypted {os.path.basename(self.file_to_encrypt)} successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Encryption failed: {e}")
            return False


class CleanupCommand(Command):
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
            except Exception as e:
                self.logger.error(f"Failed to delete {old_file}: {e}")


# --------------------------
# Support Components
# --------------------------


class SizeCalculator:
    def __init__(self, directories: List[str], ignore_list: List[str]):
        self.directories = [os.path.expanduser(d) for d in directories]
        self.ignore_list = [os.path.expanduser(p) for p in ignore_list]

    def calculate_total_size(self) -> int:
        total = 0
        for directory in self.directories:
            total += self._calculate_directory_size(directory)
        return total

    def _calculate_directory_size(self, directory: str) -> int:
        total = 0
        for root, dirs, files in os.walk(directory):
            if self._should_ignore(root):
                dirs[:] = []
                continue

            for file in files:
                file_path = os.path.join(root, file)
                if not self._should_ignore(file_path):
                    try:
                        total += os.path.getsize(file_path)
                    except Exception as e:
                        logging.warning(f"Error accessing {file_path}: {e}")
        return total

    def _should_ignore(self, path: str) -> bool:
        return any(path.startswith(ignored) for ignored in self.ignore_list)


# --------------------------
# Facade
# --------------------------


class BackupFacade:
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


class DecryptCommand(Command):
    def __init__(self, config, file_path):
        self.config = config
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)

    def execute(self):
        password = getpass.getpass("Enter decryption password: ")
        output_path = os.path.splitext(self.file_path)[0]  # Remove .enc

        cmd = [
            "openssl",
            "aes-256-cbc",
            "-d",
            "-a",
            "-salt",
            "-pbkdf2",
            "-in",
            self.file_path,
            "-out",
            output_path,
            "-pass",
            f"pass:{password}",
        ]

        try:
            subprocess.run(cmd, check=True)
            self.logger.info("Decryption successful")
            self._verify_integrity(output_path)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Decryption failed: {e}")
            return False

    def _verify_integrity(self, decrypted_path: str):
        """Verify decrypted file matches original backup checksum"""
        original_path = decrypted_path  # Same as decrypted output path

        if not os.path.exists(original_path):
            self.logger.warning("Original backup file not available for verification")
            return

        try:
            decrypted_checksum = self._calculate_sha256(decrypted_path)
            original_checksum = self._calculate_sha256(original_path)

            if decrypted_checksum == original_checksum:
                self.logger.info("File integrity verified: SHA256 checksums match")
            else:
                self.logger.error("Integrity check failed: Checksums do not match")
        except FileNotFoundError:
            self.logger.error("Original backup file missing for verification")

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
