"""Backup command implementation for creating compressed archives.

This module contains the BackupCommand class that handles the creation of
backup archives using Python's tarfile library with xz compression.
"""

import datetime
import fnmatch
import json
import logging
import os
import tarfile
from pathlib import Path

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig
from autotarcompress.utils.progress_bar import SimpleProgressBar
from autotarcompress.utils.size_calculator import SizeCalculator
from autotarcompress.utils.utils import (
    ensure_backup_folder,
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
        except (OSError, PermissionError):
            self.logger.exception("Failed to ensure backup folder")
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
        """Run the backup process using tarfile library.

        Args:
            total_size: Total size of files to back up, in bytes.

        Returns:
            True if backup succeeded, False otherwise.

        """
        if Path(self.config.backup_path).exists():
            self.logger.warning(
                "File already exists: %s",
                self.config.backup_path,
            )
            if not self._prompt_overwrite():
                msg = "Backup aborted by user due to existing file."
                self.logger.info("%s", msg)
                return False
            try:
                Path(self.config.backup_path).unlink()
                self.logger.info(
                    "Removed existing backup file: %s",
                    self.config.backup_path,
                )
            except (OSError, PermissionError):
                self.logger.exception("Failed to remove existing backup")
                return False

        total_size_gb = total_size / 1024**3

        self.logger.info(
            "Starting backup to %s",
            self.config.backup_path,
        )
        self.logger.info(
            "Total size: %.2f GB",
            total_size_gb,
        )

        # Use tarfile library for backup with progress bar
        return self._run_backup_with_tarfile(total_size)

    def _run_backup_with_tarfile(self, total_size: int) -> bool:
        """Create backup using tarfile library with progress tracking.

        Args:
            total_size: Total size in bytes for progress calculation

        Returns:
            True if backup succeeded, False otherwise

        """
        progress = SimpleProgressBar(total_size)
        initial_dev: int | None = None

        try:
            # Open tar file with zstd compression
            # zstd compression level can be customized via preset
            # parameter (1-22). Using default (preset=3) for balanced
            # speed/ratio
            with tarfile.open(str(self.config.backup_path), "w:zst") as tar:
                for directory in self.config.dirs_to_backup:
                    dir_path = Path(directory)

                    # Get device ID for --one-file-system behavior
                    if initial_dev is None:
                        initial_dev = dir_path.stat().st_dev

                    self._add_directory_to_tar(
                        tar, dir_path, progress, initial_dev
                    )

            progress.finish()
            self.logger.info("Backup completed successfully")
            return True

        except (OSError, PermissionError, tarfile.TarError):
            self.logger.exception("Backup failed")
            return False

    def _add_directory_to_tar(
        self,
        tar: tarfile.TarFile,
        directory: Path,
        progress: SimpleProgressBar,
        initial_dev: int,
    ) -> None:
        """Recursively add directory to tar with exclusions.

        Args:
            tar: TarFile object to add files to
            directory: Directory path to add
            progress: Progress bar to update
            initial_dev: Device ID for filesystem boundary detection

        """
        # Add the directory itself first
        if not self._should_exclude(directory):
            try:
                # Check filesystem boundary
                if directory.stat().st_dev != initial_dev:
                    self.logger.debug(
                        "Skipping %s (different filesystem)", directory
                    )
                    return

                arcname = directory.name
                tar.add(
                    str(directory),
                    arcname=arcname,
                    recursive=False,
                )
            except (OSError, PermissionError) as e:
                self.logger.warning("Skipping %s: %s", directory, e)
                return

        # Walk through directory contents
        for root, dirs, files in os.walk(directory, followlinks=True):
            root_path = Path(root)

            # Check filesystem boundary for root
            try:
                if root_path.stat().st_dev != initial_dev:
                    self.logger.debug(
                        "Skipping %s (different filesystem)", root_path
                    )
                    dirs[:] = []  # Don't recurse into subdirectories
                    continue
            except (OSError, PermissionError):
                dirs[:] = []
                continue

            # Filter directories in-place to skip ignored ones
            original_dirs = dirs[:]
            dirs[:] = [
                d
                for d in original_dirs
                if not self._should_exclude(root_path / d)
            ]

            # Add files
            for file in files:
                file_path = root_path / file

                if self._should_exclude(file_path):
                    continue

                try:
                    # Check filesystem boundary for file
                    file_stat = file_path.stat()
                    if file_stat.st_dev != initial_dev:
                        self.logger.debug(
                            "Skipping %s (different filesystem)", file_path
                        )
                        continue

                    # Calculate relative path from parent of directory
                    arcname_path = file_path.relative_to(directory.parent)
                    tar.add(
                        str(file_path),
                        arcname=str(arcname_path),
                    )

                    # Update progress with file size
                    progress.update(file_stat.st_size)

                except (OSError, PermissionError) as e:
                    self.logger.warning("Skipping %s: %s", file_path, e)

    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded based on ignore_list.

        Args:
            path: Path to check

        Returns:
            True if path should be excluded

        """
        path_str = str(path)

        for pattern in self.config.ignore_list:
            # Absolute path match
            if pattern.startswith("/"):
                # Pattern is already expanded in config
                if path_str.startswith(pattern):
                    return True
            # Glob pattern match on filename
            elif fnmatch.fnmatch(path.name, pattern) or pattern in path.parts:
                return True

        return False

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
                "backup_date": datetime.datetime.now(
                    tz=datetime.UTC
                ).isoformat(),
                "backup_size_bytes": total_size,
                "backup_size_human": self._format_size(total_size),
                "directories_backed_up": self.config.dirs_to_backup,
            }

            # Save the info file in the config directory
            info_file_path = (
                Path(self.config.config_dir).expanduser() / "metadata.json"
            )

            with info_file_path.open("w", encoding="utf-8") as f:
                json.dump(backup_info, f, indent=2)

            self.logger.info("Backup info saved to %s", info_file_path)

            # NOTE: Broad except is used here to ensure any error during backup
            # info saving is logged, as this is a non-critical reporting step.
        except (OSError, PermissionError, ValueError):
            self.logger.exception("Failed to save backup info")

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format."""
        bytes_in_kb = 1024.0
        size = float(size_bytes)

        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < bytes_in_kb:
                return f"{size:.2f} {unit}"
            size /= bytes_in_kb
        return f"{size:.2f} PB"
