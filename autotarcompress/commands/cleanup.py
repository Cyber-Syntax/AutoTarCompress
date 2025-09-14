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
    """Concrete command to perform cleanup of old backups."""

    def __init__(self, config: BackupConfig):
        """Initialize CleanupCommand with backup configuration.

        Args:
            config: BackupConfig instance with retention and folder settings.

        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    def execute(self) -> bool:
        """Execute cleanup process for old backup, encrypted, and decrypted files.

        Deletes old .tar.xz files (retention: keep_backup),
        .tar.xz.enc files (retention: keep_enc_backup), and
        .tar.xz-decrypted files (retention: keep_backup).
        No separate retention for decrypted files; uses keep_backup.
        """
        self._cleanup_files(".tar.xz", self.config.keep_backup)
        self._cleanup_files(".tar.xz.enc", self.config.keep_enc_backup)
        self._cleanup_files(".tar.xz-decrypted", self.config.keep_backup)
        return True

    def _cleanup_files(self, ext: str, keep_count: int) -> None:
        """Delete old backup files based on file extension and retention count.

        Args:
            ext: File extension to filter for cleanup
            keep_count: Number of recent files to keep

        """
        backup_folder = Path(self.config.backup_folder)

        # Get all files with the specified extension
        files = sorted(
            [f for f in os.listdir(backup_folder) if f.endswith(ext)],
            key=lambda x: datetime.datetime.strptime(x.split(".")[0], "%d-%m-%Y"),
        )

        # Delete files exceeding the retention count
        files_to_delete = files if keep_count == 0 else files[:-keep_count]

        for old_file in files_to_delete:
            file_path = backup_folder / old_file
            try:
                file_path.unlink()
                self.logger.info("Deleted old backup: %s", old_file)
                print(f"Deleted old backup: {old_file}")
            except Exception as e:
                self.logger.error("Failed to delete %s: %s", old_file, e)
                print(f"Failed to delete {old_file}: {e}")
