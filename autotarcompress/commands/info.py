"""Info command implementation for displaying last backup information.

This module contains the InfoCommand class that displays information about
the last backup operation.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from autotarcompress.commands.command import Command
from autotarcompress.config import BackupConfig


class InfoCommand(Command):
    """Concrete command to display last backup information."""

    def __init__(self, config: BackupConfig):
        """Initialize the info command with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)

    def execute(self) -> bool:
        """Execute info display process."""
        backup_info = self._load_backup_info()

        if backup_info:
            self._display_backup_info(backup_info)
            return True
        else:
            print("No backup information found.")
            print("This usually means no backups have been created yet.")
            return False

    def _load_backup_info(self) -> Optional[Dict[str, Any]]:
        """Load backup information from last-backup-info.json."""
        try:
            info_file_path = Path(self.config.backup_folder) / "last-backup-info.json"

            if not info_file_path.exists():
                return None

            with open(info_file_path, encoding="utf-8") as f:
                data = json.load(f)
                # Validate that the loaded data is a dictionary
                if isinstance(data, dict):
                    return data
                else:
                    self.logger.error("Backup info file does not contain a valid JSON object")
                    return None

        except json.JSONDecodeError as e:
            self.logger.error(f"Error reading backup info file: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load backup info: {e}")
            return None

    def _display_backup_info(self, backup_info: Dict[str, Any]) -> None:
        """Display backup information in a formatted way."""
        print("\n===== Last Backup Information =====")
        print(f"Backup File: {backup_info.get('backup_file', 'Unknown')}")
        print(f"Full Path: {backup_info.get('backup_path', 'Unknown')}")
        print(f"Backup Date: {backup_info.get('backup_date', 'Unknown')}")
        print(f"Backup Size: {backup_info.get('backup_size_human', 'Unknown')}")

        dirs = backup_info.get("directories_backed_up", [])
        if dirs:
            print(f"Directories Backed Up ({len(dirs)}):")
            for directory in dirs:
                print(f"  - {directory}")
        else:
            print("Directories Backed Up: None")

        # Check if backup file still exists
        backup_path = backup_info.get("backup_path")
        if backup_path and Path(backup_path).exists():
            print("Status: ✓ Backup file exists")
        elif backup_path:
            print("Status: ✗ Backup file not found")
        else:
            print("Status: Unknown")

        print("=" * 35)
