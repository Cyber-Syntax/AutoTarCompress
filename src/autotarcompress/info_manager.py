"""Info manager for handling backup information display operations.

This module contains the InfoManager class that encapsulates
the core info display logic extracted from InfoCommand.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autotarcompress.config import BackupConfig


class InfoManager:
    """Manager class for info display operations.

    Handles loading and displaying backup metadata information.
    """

    def __init__(
        self, config: BackupConfig, logger: logging.Logger | None = None
    ) -> None:
        """Initialize InfoManager.

        Args:
            config: Backup configuration
            logger: Logger instance (optional, creates default if not provided)
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def execute_info(self) -> bool:
        """Display last backup information if available.

        Returns:
            bool: True if info displayed, False otherwise.
        """
        backup_info: dict[str, Any] | None = self._load_backup_info()
        if backup_info and backup_info.get("last_backup_file"):
            self.logger.info("Backup information found.")
            self._display_backup_info(backup_info)
            return True
        self.logger.info("No backup information found.")
        self.logger.info(
            "This usually means no backups have been created yet."
        )
        return False

    def _load_backup_info(self) -> dict[str, Any] | None:
        """Load backup information from metadata.json.

        Returns:
            Optional[dict[str, Any]]: Backup info dict if found, else None.
        """
        try:
            info_file_path: Path = (
                Path(self.config.config_dir).expanduser() / "metadata.json"
            )
            if not info_file_path.exists():
                self.logger.warning("No backup info file found.")
                return None

            with info_file_path.open(encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                self.logger.error(
                    "Backup info file does not contain a valid JSON object"
                )
                return None
        except json.JSONDecodeError:
            self.logger.exception("Error reading backup info file")
            return None
        except OSError:
            self.logger.exception("Failed to load backup info")
            return None

    def _display_backup_info(self, backup_info: dict[str, Any]) -> None:
        """Display backup information in a formatted way.

        Args:
            backup_info (dict[str, Any]): Backup info dictionary.
        """
        self.logger.info("\n===== Last Backup Information =====")
        self.logger.info(
            "Backup File: %s",
            backup_info.get("last_backup_file", "Unknown"),
        )
        self.logger.info(
            "Backup Date: %s",
            backup_info.get("last_backup_time", "Unknown"),
        )
        self.logger.info(
            "Total Backups: %s",
            backup_info.get("backup_count", "Unknown"),
        )
        self.logger.info(
            "Metadata Version: %s",
            backup_info.get("metadata_version", "Unknown"),
        )

        file_hashes = backup_info.get("file_hashes", {})
        if file_hashes:
            self.logger.info("File Hashes (%d files):", len(file_hashes))
            for filename, file_hash in file_hashes.items():
                self.logger.info("  %s: %s", filename, file_hash)
        else:
            self.logger.info("File Hashes: None")

        self.logger.info("=" * 35)
