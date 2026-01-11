"""Cleanup manager for handling cleanup operations.

This module contains the CleanupManager class that encapsulates
the core cleanup logic extracted from CleanupCommand.
"""

from __future__ import annotations

import datetime
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autotarcompress.config import BackupConfig


class CleanupManager:
    """Manager class for cleanup operations.

    Handles the core cleanup logic including file discovery,
    age calculation, deletion logic, and error handling.
    """

    def __init__(
        self, config: BackupConfig, logger: logging.Logger | None = None
    ) -> None:
        """Initialize CleanupManager.

        Args:
            config: Backup configuration
            logger: Logger instance (optional, creates default if not provided)
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def execute_cleanup(self, cleanup_all: bool = False) -> bool:
        """Execute the complete cleanup process.

        Args:
            cleanup_all: If True, delete all backup files regardless
                of retention policy.

        Returns:
            True if cleanup succeeded, False otherwise
        """
        try:
            if cleanup_all:
                self._cleanup_all_files()
            else:
                # Support both new (.tar.zst) and legacy (.tar.xz) formats
                self._cleanup_files(".tar.zst", self.config.keep_backup)
                self._cleanup_files(".tar.xz", self.config.keep_backup)
                self._cleanup_files(
                    ".tar.zst-decrypted", self.config.keep_backup
                )
                self._cleanup_files(
                    ".tar.xz-decrypted", self.config.keep_backup
                )
                self._cleanup_files(".tar-extracted", self.config.keep_backup)
                self._cleanup_files(
                    ".tar.zst.enc", self.config.keep_enc_backup
                )
                self._cleanup_files(".tar.xz.enc", self.config.keep_enc_backup)
        except (OSError, PermissionError, ValueError):
            self.logger.exception("Cleanup failed")
            return False
        else:
            return True

    def _cleanup_files(self, ext: str, keep_count: int) -> None:
        """Delete old files by extension.

        Keeping only the most recent as configured.

        Args:
            ext: File extension to filter for cleanup.
            keep_count: Number of recent files to keep.
        """
        backup_folder: Path = Path(self.config.backup_folder).expanduser()
        files: list[str] = sorted(
            [f.name for f in backup_folder.iterdir() if f.name.endswith(ext)],
            key=self._extract_date_from_filename,
        )

        files_to_delete: list[str] = (
            files if keep_count == 0 else files[:-keep_count]
        )
        if not files_to_delete:
            self.logger.info("No old '%s' files to remove.", ext)
            return

        for old_file in files_to_delete:
            file_path = backup_folder / old_file
            try:
                if file_path.is_dir():
                    # Remove directory (recursively if not empty)
                    shutil.rmtree(file_path)
                    self.logger.info(
                        "Deleted old backup directory: %s", old_file
                    )
                else:
                    file_path.unlink()
                    self.logger.info("Deleted old backup: %s", old_file)
            except (OSError, PermissionError):
                self.logger.exception("Failed to delete %s", old_file)

    def _cleanup_all_files(self) -> None:
        """Delete all backup files regardless of retention policy.

        This method removes all backup files of all types without
        respecting the keep_count configuration.
        """
        # Support both new (.tar.zst) and legacy (.tar.xz) formats
        extensions = [
            ".tar.zst",
            ".tar.xz",
            ".tar.zst-decrypted",
            ".tar.xz-decrypted",
            ".tar-extracted",
            ".tar.zst.enc",
            ".tar.xz.enc",
        ]

        for ext in extensions:
            self._cleanup_files(ext, 0)  # keep_count=0 means delete all

    def _extract_date_from_filename(self, filename: str) -> datetime.datetime:
        """Extract datetime from filename for sorting.

        Args:
            filename: Filename with date format at start.

        Returns:
            Parsed datetime object.
        """
        return datetime.datetime.strptime(
            filename.split(".")[0], "%d-%m-%Y"
        ).replace(tzinfo=datetime.UTC)
