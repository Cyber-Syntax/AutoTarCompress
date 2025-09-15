"""Backup command implementation for creating compressed archives.

This module contains the BackupCommand class that handles the creation of
backup archives using tar and xz compression.
"""

import datetime
import itertools
import json
import logging
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig
from autotarcompress.utils import SizeCalculator


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
        if not self.config.dirs_to_backup:
            self._print_and_log(
                "No directories configured for backup. Skipping backup.", level="error"
            )
            return False
        total_size: int = self._calculate_total_size()
        if total_size == 0:
            self._print_and_log(
                "Total backup size is 0 bytes. Nothing to back up.", level="warning"
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
        calculator = SizeCalculator(self.config.dirs_to_backup, self.config.ignore_list)
        return calculator.calculate_total_size()

    def _run_backup_process(self, total_size: int) -> bool:
        """Run the backup process and return success status.

        Args:
            total_size (int): Total size of files to back up, in bytes.

        Returns:
            bool: True if backup succeeded, False otherwise.

        """
        if os.path.exists(self.config.backup_path):
            self._print_and_log(f"File already exists: {self.config.backup_path}", level="warning")
            if not self._prompt_overwrite():
                self._print_and_log("Backup aborted by user due to existing file.", level="info")
                return False
            try:
                os.remove(self.config.backup_path)
                self.logger.info("Removed existing backup file: %s", self.config.backup_path)
            # NOTE: Broad except is used here to ensure any file removal error
            # is caught during backup overwrite prompt. This is a critical IO
            # operation.
            except Exception as e:
                self._print_and_log(f"Failed to remove existing backup: {e}", level="error")
                return False

        cmd = self._build_tar_command()
        total_size_gb = total_size / 1024**3

        self.logger.info("Starting backup to %s", self.config.backup_path)
        self.logger.info("Total size: %.2f GB", total_size_gb)

        try:
            subprocess.run(cmd, shell=True, check=True)
            self.logger.info("Backup completed successfully")
            self._print_and_log("Backup completed successfully.", level="info")
            return True
        except subprocess.CalledProcessError as e:
            self._print_and_log(f"Backup failed: {e}", level="error")
            return False

    def _build_tar_command(self) -> str:
        """Build the tar+xz command string for backup."""
        exclude_options = " ".join(f"--exclude={path}" for path in self.config.ignore_list)
        dir_paths = [os.path.expanduser(path) for path in self.config.dirs_to_backup]
        quoted_paths = [shlex.quote(path) for path in dir_paths]
        cpu_count = os.cpu_count() or 1
        threads = max(1, cpu_count - 1)
        return (
            f"tar -chf - --one-file-system {exclude_options} "
            f"{' '.join(quoted_paths)} | "
            f"xz --threads={threads} > {self.config.backup_path}"
        )

    def _prompt_overwrite(self) -> bool:
        """Prompt user to overwrite existing backup file."""
        response = input("Do you want to remove it? (y/n): ").strip().lower()
        return response == "y"

    def _print_and_log(self, message: str, level: str = "info") -> None:
        """Print and log a message at the specified level."""
        print(message)
        if level == "info":
            self.logger.info(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        else:
            self.logger.debug(message)

    def _save_backup_info(self, total_size: int) -> None:
        """Save backup information to last-backup-info.json."""
        try:
            backup_info = {
                "backup_file": Path(self.config.backup_path).name,
                "backup_path": str(self.config.backup_path),
                "backup_date": datetime.datetime.now().isoformat(),
                "backup_size_bytes": total_size,
                "backup_size_human": self._format_size(total_size),
                "directories_backed_up": self.config.dirs_to_backup,
            }

            # Save the info file in the backup folder
            info_file_path = Path(self.config.backup_folder) / "last-backup-info.json"

            with open(info_file_path, "w", encoding="utf-8") as f:
                json.dump(backup_info, f, indent=2)

            self.logger.info("Backup info saved to %s", info_file_path)

            # NOTE: Broad except is used here to ensure any error during backup
            # info saving is logged, as this is a non-critical reporting step.
        except Exception as e:
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

    def _show_spinner(self, process) -> None:
        spinner = itertools.cycle(["/", "-", "\\", "|"])
        while process.poll() is None:
            sys.stdout.write(next(spinner) + " ")
            sys.stdout.flush()
            sys.stdout.write("\b\b")
            time.sleep(0.1)
