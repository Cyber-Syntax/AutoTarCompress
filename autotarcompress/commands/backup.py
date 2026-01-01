"""Backup command implementation for creating compressed archives.

This module contains the BackupCommand class that handles the creation of
backup archives using tar and xz compression.
"""

import datetime
import json
import logging
import os
import shlex
import subprocess
from pathlib import Path

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig
from autotarcompress.utils import (
    SizeCalculator,
    ensure_backup_folder,
    is_pv_available,
    validate_and_expand_paths,
)


class BackupCommand(Command):
    """Command to create compressed backup archives using tar and xz."""

    def __init__(self, config: BackupConfig) -> None:
        """Initialize BackupCommand.

        Args:
            config (BackupConfig): Backup configuration object.

        """
        self.config: BackupConfig = config
        self.logger: logging.Logger = logging.getLogger(__name__)

    def execute(self) -> bool:
        """Execute backup process.

        Returns:
            bool: True if backup succeeded, False otherwise.

        """
        # Validate and ensure backup directories
        existing_dirs, missing_dirs = validate_and_expand_paths(
            self.config.dirs_to_backup
        )
        if missing_dirs:
            # Log missing directories; no need to print to stdout here.
            self.logger.warning(
                "Some configured backup directories do not exist: %s",
                missing_dirs,
            )

        # Use equality comparison instead of identity; lists with the same
        # contents should be compared by value.
        if existing_dirs != self.config.dirs_to_backup:
            self.logger.info(
                "Proceeding with existing directories only: %s",
                existing_dirs,
            )
            self.config.dirs_to_backup = existing_dirs

        # Ensure backup folder exists
        try:
            backup_folder_path = ensure_backup_folder(
                self.config.backup_folder
            )
            self.config.backup_folder = str(backup_folder_path)
            self.logger.info(
                "Backup folder ensured at: %s",
                self.config.backup_folder,
            )
        except (OSError, PermissionError) as e:
            self.logger.error("Failed to ensure backup folder: %s", e)
            return False

        if not self.config.dirs_to_backup:
            self.logger.error(
                "No directories configured for backup. Skipping backup."
            )
            return False
        total_size: int = self._calculate_total_size()
        if total_size == 0:
            self.logger.warning(
                "Total backup size is 0 bytes. Nothing to back up."
            )
            return False
        success: bool = self._run_backup_process(total_size)
        if success:
            self._save_backup_info(total_size)
        return success

    def _calculate_total_size(self) -> int:
        """Calculate total size of all directories to back up.

        Returns:
            int: Total size in bytes.

        """
        calculator = SizeCalculator(
            self.config.dirs_to_backup,
            self.config.ignore_list,
        )
        return calculator.calculate_total_size()

    def _run_backup_process(self, total_size: int) -> bool:
        """Run the backup process and return success status.

        Args:
            total_size (int): Total size of files to back up, in bytes.

        Returns:
            bool: True if backup succeeded, False otherwise.

        """
        if os.path.exists(self.config.backup_path):
            self.logger.warning(
                "File already exists: %s",
                self.config.backup_path,
            )
            if not self._prompt_overwrite():
                msg = "Backup aborted by user due to existing file."
                self.logger.info("%s", msg)
                return False
            try:
                os.remove(self.config.backup_path)
                self.logger.info(
                    "Removed existing backup file: %s",
                    self.config.backup_path,
                )
            # NOTE: Broad except is used here to ensure any file removal error
            # is caught during backup overwrite prompt. This is a critical IO
            # operation.
            except (OSError, PermissionError) as e:
                self.logger.error("Failed to remove existing backup: %s", e)
                return False

        cmd = self._build_tar_command(total_size)
        total_size_gb = total_size / 1024**3

        self.logger.info(
            "Starting backup to %s",
            self.config.backup_path,
        )
        self.logger.info(
            "Total size: %.2f GB",
            total_size_gb,
        )

        try:
            subprocess.run(cmd, shell=True, check=True)
            self.logger.info("Backup completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error("Backup failed: %s", e)
            return False

    def _build_tar_command(self, total_size: int) -> str:
        """Build the tar+xz command string for backup with optional pv progress.

        Args:
            total_size (int): Total size in bytes for pv progress calculation.

        Returns:
            str: The complete command string for backup.

        """
        # Quote each exclude pattern for shell safety
        exclude_options = " ".join(
            f"--exclude={shlex.quote(pattern)}"
            for pattern in self.config.ignore_list
        )
        dir_paths = [
            os.path.expanduser(path) for path in self.config.dirs_to_backup
        ]
        quoted_paths = [shlex.quote(path) for path in dir_paths]
        cpu_count = os.cpu_count() or 1
        threads = max(1, cpu_count - 1)

        # Build tar command with pv progress if available
        tar_cmd = (
            f"tar -chf - --one-file-system {exclude_options} "
            f"{' '.join(quoted_paths)}"
        )

        if is_pv_available():
            # Use pv to show progress bar
            return (
                f"{tar_cmd} | "
                f"pv -s {total_size} | "
                f"xz --threads={threads} > {self.config.backup_path}"
            )
        # Fallback without progress bar
        self.logger.info(
            "pv command not found. Progress bar disabled. "
            "Install pv for progress visualization: sudo apt install pv"
        )
        return (
            f"{tar_cmd} | xz --threads={threads} > {self.config.backup_path}"
        )

    def _prompt_overwrite(self) -> bool:
        """Prompt user to overwrite existing backup file."""
        response = input("Do you want to remove it? (y/n): ").strip().lower()
        return response == "y"

    def _save_backup_info(self, total_size: int) -> None:
        """Save backup information to metadata.json."""
        try:
            backup_info = {
                "backup_file": Path(self.config.backup_path).name,
                "backup_path": str(self.config.backup_path),
                "backup_date": datetime.datetime.now().isoformat(),
                "backup_size_bytes": total_size,
                "backup_size_human": self._format_size(total_size),
                "directories_backed_up": self.config.dirs_to_backup,
            }

            # Save the info file in the config directory
            info_file_path = (
                Path(self.config.config_dir).expanduser() / "metadata.json"
            )

            with open(info_file_path, "w", encoding="utf-8") as f:
                json.dump(backup_info, f, indent=2)

            self.logger.info("Backup info saved to %s", info_file_path)

            # NOTE: Broad except is used here to ensure any error during backup
            # info saving is logged, as this is a non-critical reporting step.
        except (OSError, PermissionError, ValueError) as e:
            self.logger.error("Failed to save backup info: %s", e)

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format."""
        BYTES_IN_KB = 1024.0
        size = float(size_bytes)

        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < BYTES_IN_KB:
                return f"{size:.2f} {unit}"
            size /= BYTES_IN_KB
        return f"{size:.2f} PB"
