"""Cleanup command for managing old backup files.

This module contains the CleanupCommand class that handles the deletion
of old backup files according to retention policies.
"""

import datetime
import logging
import os
from pathlib import Path

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig


class CleanupCommand(Command):
    """Command to clean up old backup, encrypted, and decrypted files."""

    def __init__(self, config: BackupConfig) -> None:
        """Initialize CleanupCommand.

        Args:
            config (BackupConfig): Backup configuration with retention and
                folder settings.

        """
        self.config: BackupConfig = config
        self.logger: logging.Logger = logging.getLogger(__name__)

    def execute(self) -> bool:
        """Delete old backup, encrypted, and decrypted files.

        Per retention policy.

        Returns:
            bool: Always True (cleanup always completes, even if nothing
                to delete).

        """
        self._cleanup_files(".tar.xz", self.config.keep_backup)
        self._cleanup_files(".tar.xz.enc", self.config.keep_enc_backup)
        self._cleanup_files(".tar.xz-decrypted", self.config.keep_backup)
        return True

    def _cleanup_files(self, ext: str, keep_count: int) -> None:
        """Delete old files by extension.

        Keeping only the most recent as configured.

        Args:
            ext (str): File extension to filter for cleanup.
            keep_count (int): Number of recent files to keep.

        """

        def _extract_date_from_filename(filename: str) -> datetime.datetime:
            """Extract datetime from filename for sorting.

            Args:
                filename (str): Filename with date format at start.

            Returns:
                datetime.datetime: Parsed datetime object.

            """
            return datetime.datetime.strptime(filename.split(".")[0], "%d-%m-%Y")

        backup_folder: Path = Path(self.config.backup_folder)
        files: list[str] = sorted(
            [f for f in os.listdir(backup_folder) if f.endswith(ext)],
            key=_extract_date_from_filename,
        )
        files_to_delete: list[str] = files if keep_count == 0 else files[:-keep_count]
        if not files_to_delete:
            msg = f"No old '{ext}' files to remove."
            print(msg)
            self.logger.info("No old '%s' files to remove.", ext)
            return None
        for old_file in files_to_delete:
            file_path = backup_folder / old_file
            try:
                file_path.unlink()
                self.logger.info("Deleted old backup: %s", old_file)
                print(f"Deleted old backup: {old_file}")
            except (OSError, PermissionError) as e:
                self.logger.error("Failed to delete %s: %s", old_file, e)
                print(f"Failed to delete {old_file}: {e}")
        return None
