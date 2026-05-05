"""Backup manager for handling backup operations.

This module contains the BackupManager class that encapsulates
the core backup logic extracted from BackupCommand.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

from autotarcompress.metadata import update_backup_metadata
from autotarcompress.utils.hash_utils import calculate_sha256
from autotarcompress.utils.progress_bar import SimpleProgressBar
from autotarcompress.utils.size_calculator import SizeCalculator
from autotarcompress.utils.utils import (
    ensure_backup_folder,
    validate_and_expand_paths,
)

if TYPE_CHECKING:
    from autotarcompress.config import BackupConfig


class BackupManager:
    """Manager class for backup operations.

    Handles the core backup logic including size calculation,
    tarfile creation, progress tracking, and metadata saving.
    """

    def __init__(
        self, config: BackupConfig, logger: logging.Logger | None = None
    ) -> None:
        """Initialize BackupManager.

        Args:
            config: Backup configuration
            logger: Logger instance (optional, creates default if not provided)
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def calculate_total_size(self) -> int:
        """Calculate total size of all directories to back up.

        Returns:
            Total size in bytes
        """
        calculator = SizeCalculator(
            self.config.dirs_to_backup,
            self.config.ignore_list,
        )
        return calculator.calculate_total_size()

    def run_backup_process(self, total_size: int) -> bool:
        """Run the backup process using tarfile library.

        Uses a temporary file + atomic rename to avoid TOCTOU issues
        and prevent partial archive corruption.

        Args:
            total_size: Total size of files to back up, in bytes.

        Returns:
            True if backup succeeded, False otherwise.
        """
        final_path = Path(self.config.backup_path)
        temp_path = final_path.with_suffix(final_path.suffix + ".tmp")

        if final_path.exists():
            self.logger.warning(
                "Backup file already exists: %s",
                final_path,
            )
            return False  # Let command handle prompting

        total_size_gb = total_size / 1024**3

        self.logger.info("Starting backup to %s", final_path)
        self.logger.info("Total size: %.2f GB", total_size_gb)

        progress = SimpleProgressBar(total_size)

        try:
            # Write to temporary file first
            with tarfile.open(str(temp_path), "w:zst") as tar:
                initial_dev: int | None = None

                for directory in self.config.dirs_to_backup:
                    dir_path = Path(directory)

                    if initial_dev is None:
                        initial_dev = dir_path.stat().st_dev

                    self._add_directory_to_tar(
                        tar, dir_path, progress, initial_dev
                    )

            progress.finish()

            # Atomic replace (this eliminates race conditions)
            Path.replace(temp_path, final_path)

        except OSError, tarfile.TarError:
            self.logger.exception("Backup failed")

            # Cleanup partial archive
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                self.logger.exception("Failed to clean up temp backup file")

            return False

        else:
            self.logger.info("Backup completed successfully")
            return True

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
        # Check filesystem boundary for directory
        try:
            if directory.stat().st_dev != initial_dev:
                self.logger.debug(
                    "Skipping %s (different filesystem)", directory
                )
                return
        except OSError:
            return

        # Add the directory itself if not excluded
        if not self._should_exclude(directory):
            try:
                arcname = directory.name
                tar.add(str(directory), arcname=arcname, recursive=False)
            except OSError as e:
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
            except OSError:
                dirs[:] = []
                continue

            # Filter directories in-place to skip ignored ones
            dirs[:] = [
                d for d in dirs if not self._should_exclude(root_path / d)
            ]

            # Add files
            for file in files:
                self._add_file_to_tar(
                    file_path=root_path / file,
                    tar=tar,
                    progress=progress,
                    initial_dev=initial_dev,
                    directory=directory,
                )

    def _add_file_to_tar(
        self,
        file_path: Path,
        tar: tarfile.TarFile,
        progress: SimpleProgressBar,
        initial_dev: int,
        directory: Path,
    ) -> None:
        """Add a single file to the tar archive.

        Args:
            file_path: Path to the file to add
            tar: TarFile object
            progress: Progress bar to update
            initial_dev: Device ID for filesystem boundary
            directory: Base directory for relative path calculation
        """
        if self._should_exclude(file_path):
            return

        try:
            # Check filesystem boundary for file
            file_stat = file_path.stat()
            if file_stat.st_dev != initial_dev:
                self.logger.debug(
                    "Skipping %s (different filesystem)", file_path
                )
                return

            # Calculate relative path from parent of directory
            arcname_path = file_path.relative_to(directory.parent)
            tar.add(str(file_path), arcname=str(arcname_path))

            # Update progress with file size
            progress.update(file_stat.st_size)

        except OSError as e:
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

    def save_backup_metadata_with_hash(self, backup_path: Path) -> None:
        """Calculate backup hash and save metadata.

        Args:
            backup_path: Path to the created backup file
        """
        try:
            self.logger.info("Calculating SHA256 hash of backup archive...")
            backup_hash = calculate_sha256(backup_path)
            self.logger.debug("Backup hash: %s", backup_hash[:16])

            # Update metadata with backup file and hash
            update_backup_metadata(
                Path(self.config.config_dir),
                backup_path,
                backup_hash,
            )
        except OSError:
            self.logger.exception(
                "Failed to calculate backup hash or save metadata"
            )
            # Try to update metadata without hash if possible
            try:
                update_backup_metadata(
                    Path(self.config.config_dir),
                    backup_path,
                    None,
                )
            except OSError:
                self.logger.exception("Failed to save metadata without hash")

    def execute_backup(self) -> bool:
        """Execute the complete backup process.

        Returns:
            True if backup succeeded, False otherwise
        """
        existing_dirs, missing_dirs = validate_and_expand_paths(
            self.config.dirs_to_backup
        )

        if missing_dirs:
            self.logger.warning(
                "Some configured backup directories do not exist: %s",
                missing_dirs,
            )

        if existing_dirs != self.config.dirs_to_backup:
            self.logger.info(
                "Proceeding with existing directories only: %s",
                existing_dirs,
            )
            self.config.dirs_to_backup = existing_dirs

        try:
            backup_folder_path = ensure_backup_folder(
                self.config.backup_folder
            )
            self.config.backup_folder = str(backup_folder_path)
        except OSError:
            self.logger.exception("Failed to ensure backup folder")
            return False

        if not self.config.dirs_to_backup:
            self.logger.error("No directories configured for backup.")
            return False

        total_size: int = self.calculate_total_size()
        if total_size == 0:
            self.logger.warning("Nothing to back up.")
            return False

        backup_path = Path(self.config.backup_path)

        # if the user confirms, we delete the file BEFORE proceeding.
        if backup_path.exists():
            if not self._prompt_overwrite(backup_path):
                self.logger.info("Backup aborted by user.")
                return False

            # User said yes — delete the existing file now so run_backup_process
            # can write a fresh archive in its place.
            try:
                backup_path.unlink()
                self.logger.info(
                    "Removed existing backup: %s", backup_path.name
                )
            except OSError:
                self.logger.exception(
                    "Failed to remove existing backup file: %s", backup_path
                )
                return False

        success = self.run_backup_process(total_size)

        if success:
            self.save_backup_metadata_with_hash(Path(self.config.backup_path))

        return success

    def _prompt_overwrite(self, backup_path: Path) -> bool:
        """Ask the user whether to overwrite an existing backup file.

        Args:
            backup_path: Path to the backup file that already exists.
                         Shown to the user so they know exactly what
                         will be deleted.

        Returns:
            True if the user wants to overwrite, False otherwise.
        """
        print(f"Backup already exists: {backup_path}")
        response = (
            input("Do you want to overwrite it? (y/n): ").strip().lower()
        )
        return response == "y"