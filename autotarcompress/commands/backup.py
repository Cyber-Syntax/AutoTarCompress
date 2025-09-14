"""Backup command implementation for creating compressed archives.

This module contains the BackupCommand class that handles the creation of backup archives
using tar and xz compression.
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
            msg = "No directories configured for backup. Skipping backup."
            print(msg)
            self.logger.error("No directories configured for backup. Skipping backup.")
            return False
        total_size: int = self._calculate_total_size()
        if total_size == 0:
            msg = "Total backup size is 0 bytes. Nothing to back up."
            print(msg)
            self.logger.warning("Total backup size is 0 bytes. Nothing to back up.")
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
            print(f"File already exists: {self.config.backup_path}")
            self.logger.warning("Backup file already exists: %s", self.config.backup_path)
            if input("Do you want to remove it? (y/n): ").lower() == "y":
                try:
                    os.remove(self.config.backup_path)
                    self.logger.info("Removed existing backup file: %s", self.config.backup_path)
                except Exception as e:
                    print(f"Failed to remove existing backup: {e}")
                    self.logger.error("Failed to remove existing backup: %s", e)
                    return False
            else:
                print("Backup aborted by user.")
                self.logger.info("Backup aborted by user due to existing file.")
                return False

        exclude_options = " ".join(f"--exclude={path}" for path in self.config.ignore_list)

        dir_paths = [os.path.expanduser(path) for path in self.config.dirs_to_backup]

        # Properly quote directory paths to handle spaces and special characters
        quoted_paths = [shlex.quote(path) for path in dir_paths]

        # Get CPU count safely
        cpu_count = os.cpu_count() or 1
        threads = max(1, cpu_count - 1)

        # HACK: h option is used to follow symlinks
        cmd = (
            f"tar -chf - --one-file-system {exclude_options} "
            f"{' '.join(quoted_paths)} | "
            f"xz --threads={threads} > {self.config.backup_path}"
        )
        total_size_gb = total_size / 1024**3

        self.logger.info(f"Starting backup to {self.config.backup_path}")
        self.logger.info(f"Total size: {total_size_gb:.2f} GB")

        try:
            # FIX: later spinner not working for now
            # FAILED: not work as expected because of
            # "| tar: Removing leading `/' from member names" outputs
            # self._show_spinner(subprocess.Popen(cmd, shell=True))
            subprocess.run(cmd, shell=True, check=True)
            self.logger.info("Backup completed successfully")
            print("Backup completed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Backup failed: {e}")
            self.logger.error(f"Backup failed: {e}")
            return False

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

            self.logger.info(f"Backup info saved to {info_file_path}")

        except Exception as e:
            self.logger.error(f"Failed to save backup info: {e}")

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
