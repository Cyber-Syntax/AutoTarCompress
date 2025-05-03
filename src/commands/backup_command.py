"""Backup command implementation for creating compressed archives.

This module contains the BackupCommand class that handles the creation of backup archives
using tar and xz compression.
"""

import itertools
import logging
import os
import subprocess
import sys
import time

from src.commands.command import Command
from src.config import BackupConfig
from src.utils import SizeCalculator


class BackupCommand(Command):
    """Concrete command to perform backup"""

    def __init__(self, config: BackupConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def execute(self) -> bool:
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

    def _run_backup_process(self, total_size: int) -> None:
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

    def _show_spinner(self, process) -> None:
        spinner = itertools.cycle(["/", "-", "\\", "|"])
        while process.poll() is None:
            sys.stdout.write(next(spinner) + " ")
            sys.stdout.flush()
            sys.stdout.write("\b\b")
            time.sleep(0.1)
